"""The blog application: reading pages, login, the admin editor, and the JSON API.

Build it with ``create_app(Settings.from_env())`` and serve it with any ASGI
server (blog.py uses uvicorn). It stands alone: nothing else needs to run.
"""

import asyncio
from math import ceil
from pathlib import Path
from urllib.parse import quote

from starlette.applications import Starlette
from starlette.datastructures import MutableHeaders
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import media, pages
from .auth import SESSION_COOKIE, SESSION_SECONDS, Auth, LoginThrottle
from .config import Settings, load_or_create_secret
from .render import render_markdown
from .store import MAX_BODY_CHARS, BlogError, BlogStore, Conflict, NotFound

PAGE_SIZE = 10
ADMIN_PAGE_SIZE = 25
MAX_REQUEST_BYTES = media.MAX_IMAGE_BYTES + 1024 * 1024  # an image plus form overhead; nothing larger is ever read
STATIC_DIR = Path(__file__).parent / "static"

CONTENT_SECURITY_POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' https: data:; connect-src 'self'; "
    "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

NOTICES = {
    "created": "Draft saved.",
    "saved": "Saved.",
    "published": "Published.",
    "unpublished": "Moved back to drafts.",
    "deleted": "Post deleted.",
}


class SecurityHeaders:
    """Adds the security and caching headers to every response."""

    def __init__(self, app, indexable: bool):
        self.app = app
        self.indexable = indexable

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        static = scope["path"].startswith("/static/")

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
                if not self.indexable:
                    headers.setdefault("X-Robots-Tag", "noindex, nofollow, noarchive")
                headers.setdefault("Cache-Control", "public, max-age=3600" if static else "private, no-store")
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodyLimit:
    """Rejects any request body over `max_bytes`, whether or not it declares a length."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > self.max_bytes):
            await PlainTextResponse("Request body too large", status_code=413)(scope, receive, send)
            return
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise HTTPException(status_code=413, detail="Request body too large")
            return message

        await self.app(scope, limited_receive, send)


def safe_next(value: str | None, default: str = "/admin") -> str:
    """Only allow a same-site path as a post-login destination (never an absolute or protocol-relative URL)."""
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value and value.isprintable():
        return value
    return default


def _field(form, name: str) -> str:
    value = form.get(name, "")
    return value if isinstance(value, str) else ""


def _page_number(request: Request) -> int:
    try:
        return min(max(1, int(request.query_params.get("page", "1"))), 1_000_000)
    except ValueError:
        return 1


class BlogApp:
    """Holds the blog's state and implements its request handlers."""

    login_delay = 0.5  # seconds to stall a failed login, on top of the lockout

    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = BlogStore(settings.data_dir)
        data_dir = self.store.data_dir
        self.password_file = data_dir / "blog_password"
        self.api_token_file = data_dir / "api_token"
        self.password = settings.password or load_or_create_secret(self.password_file)
        self.password_source = "BLOG_PASSWORD" if settings.password else str(self.password_file)
        self.api_token = settings.api_token or load_or_create_secret(self.api_token_file, 32)
        self.api_token_source = "BLOG_API_TOKEN" if settings.api_token else str(self.api_token_file)
        self.auth = Auth(settings.username, self.password, load_or_create_secret(data_dir / "secret_key", 32), self.api_token)
        self.throttle = LoginThrottle()
        self.media_dir = data_dir / "media"
        self.site = {"title": settings.title, "description": settings.description}

    # --- request helpers ---------------------------------------------------

    def session(self, request: Request) -> dict | None:
        if not hasattr(request.state, "session"):
            request.state.session = self.auth.read_session(request.cookies.get(SESSION_COOKIE))
        return request.state.session

    def ctx(self, request: Request) -> dict:
        session = self.session(request)
        return {
            "site": self.site,
            "user": session["u"] if session else None,
            "csrf": session["csrf"] if session else None,
            "indexable": self.settings.public,
        }

    def html(self, request: Request, content: str, status: int = 200) -> HTMLResponse:
        return HTMLResponse(content, status_code=status)

    def not_found(self, request: Request, message: str = "That page does not exist.") -> HTMLResponse:
        return self.html(request, pages.not_found_page(self.ctx(request), message), 404)

    def to_login(self, request: Request) -> RedirectResponse:
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(f"/login?next={quote(target, safe='/')}", status_code=303)

    def can_read(self, request: Request) -> bool:
        """Published posts are readable by anyone in public mode, otherwise only when logged in."""
        return self.settings.public or self.session(request) is not None

    def admin_session(self, request: Request) -> dict | Response:
        """The logged-in session, or the response that sends the visitor to log in."""
        session = self.session(request)
        if session is None:
            if request.url.path in ("/admin/preview", "/admin/upload"):
                return JSONResponse({"error": "You are logged out. Reload the page and log in again."}, status_code=401)
            return self.to_login(request)
        return session

    def csrf_failed(self, request: Request) -> HTMLResponse:
        return self.html(request, pages.message_page(self.ctx(request), "Session expired",
                                                     "That form is no longer valid. Go back, reload the page, and try again."), 403)

    def public_base(self, request: Request) -> str:
        return self.settings.public_url or str(request.base_url).rstrip("/")

    # --- reading pages -----------------------------------------------------

    async def home(self, request: Request) -> Response:
        if not self.can_read(request):
            return self.to_login(request)
        page = _page_number(request)
        listing = self.store.list_posts(status="published", limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
        return self.html(request, pages.post_list(self.ctx(request), "Posts", listing, "/", page, PAGE_SIZE,
                                                  "No posts have been published yet."))

    async def post(self, request: Request) -> Response:
        if not self.can_read(request):
            return self.to_login(request)
        try:
            post = self.store.get_post(request.path_params["slug"])
        except NotFound:
            return self.not_found(request, "There is no post with that address.")
        if post["status"] == "draft" and self.session(request) is None:
            return self.not_found(request, "There is no post with that address.")
        return self.html(request, pages.post_page(self.ctx(request), post, render_markdown(post["body"])))

    async def tag(self, request: Request) -> Response:
        if not self.can_read(request):
            return self.to_login(request)
        name = request.path_params["tag"]
        page = _page_number(request)
        listing = self.store.list_posts(status="published", tag=name, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
        return self.html(request, pages.post_list(self.ctx(request), f"Tagged #{name}", listing, f"/tag/{quote(name, safe='')}",
                                                  page, PAGE_SIZE, "No published posts have this tag."))

    async def tags(self, request: Request) -> Response:
        if not self.can_read(request):
            return self.to_login(request)
        return self.html(request, pages.tags_page(self.ctx(request), self.store.list_tags(status="published")["tags"]))

    async def search(self, request: Request) -> Response:
        if not self.can_read(request):
            return self.to_login(request)
        text = request.query_params.get("q", "").strip()[:200]
        if not text:
            return self.html(request, pages.search_page(self.ctx(request), "", None))
        status = "all" if self.session(request) else "published"
        found = self.store.search_posts(text, status=status, limit=50)["posts"]
        return self.html(request, pages.search_page(self.ctx(request), text, found))

    async def media_file(self, request: Request) -> Response:
        path = media.media_path(self.media_dir, request.path_params["name"]) if self.can_read(request) else None
        if path is None:
            return PlainTextResponse("Not found", status_code=404)
        return FileResponse(path, media_type=media.MEDIA_TYPES[path.suffix[1:]], headers={
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Cache-Control": "private, max-age=86400",
        })

    async def healthz(self, request: Request) -> Response:
        return PlainTextResponse("ok")

    async def robots(self, request: Request) -> Response:
        if self.settings.public:
            return PlainTextResponse("User-agent: *\nDisallow: /admin\nDisallow: /login\nDisallow: /api\n")
        return PlainTextResponse("User-agent: *\nDisallow: /\n")

    # --- login / logout ----------------------------------------------------

    @staticmethod
    def client_key(request: Request) -> str:
        return request.client.host if request.client else "unknown"

    async def login_form(self, request: Request) -> Response:
        next_url = safe_next(request.query_params.get("next"))
        if self.session(request):
            return RedirectResponse(next_url, status_code=303)
        return self.html(request, pages.login_page(self.ctx(request), next_url=next_url))

    async def login(self, request: Request) -> Response:
        form = await request.form()
        next_url = safe_next(_field(form, "next"))
        key = self.client_key(request)
        wait = self.throttle.retry_after(key)
        if wait:
            minutes = ceil(wait / 60)
            message = f"Too many failed attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}."
            page = pages.login_page(self.ctx(request), message, next_url, _field(form, "username"))
            return HTMLResponse(page, status_code=429, headers={"Retry-After": str(wait)})
        if not self.auth.check_login(_field(form, "username"), _field(form, "password")):
            self.throttle.record_failure(key)
            await asyncio.sleep(self.login_delay)
            wrong = pages.login_page(self.ctx(request), "Wrong username or password.", next_url, _field(form, "username"))
            return self.html(request, wrong, 401)
        self.throttle.reset(key)
        cookie, _ = self.auth.new_session()
        response = RedirectResponse(next_url, status_code=303)
        response.set_cookie(SESSION_COOKIE, cookie, max_age=SESSION_SECONDS, httponly=True, samesite="lax",
                            secure=request.url.scheme == "https", path="/")
        return response

    async def logout(self, request: Request) -> Response:
        session = self.session(request)
        form = await request.form()
        if session is not None and not Auth.check_csrf(session, _field(form, "csrf")):
            return self.csrf_failed(request)
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    # --- admin -------------------------------------------------------------

    async def dashboard(self, request: Request) -> Response:
        session = self.admin_session(request)
        if isinstance(session, Response):
            return session
        status = request.query_params.get("status", "all")
        if status not in ("all", "draft", "published"):
            status = "all"
        page = _page_number(request)
        listing = self.store.list_posts(status=status, limit=ADMIN_PAGE_SIZE, offset=(page - 1) * ADMIN_PAGE_SIZE)
        notice = NOTICES.get(request.query_params.get("msg", ""), "")
        dashboard = pages.dashboard_page(self.ctx(request), listing, self.store.stats(), status, page, ADMIN_PAGE_SIZE, notice)
        return self.html(request, dashboard)

    @staticmethod
    def _form_values(form) -> dict:
        return {name: _field(form, name).replace("\r\n", "\n") for name in ("title", "slug", "tags", "summary", "body")}

    @staticmethod
    def _tag_list(text: str) -> list[str]:
        return [part for part in text.split(",") if part.strip()]

    async def new_form(self, request: Request) -> Response:
        session = self.admin_session(request)
        if isinstance(session, Response):
            return session
        return self.html(request, pages.editor_page(self.ctx(request), None, {}))

    async def create(self, request: Request) -> Response:
        session = self.admin_session(request)
        if isinstance(session, Response):
            return session
        form = await request.form(max_part_size=4 * MAX_BODY_CHARS + 1024)
        if not Auth.check_csrf(session, _field(form, "csrf")):
            return self.csrf_failed(request)
        values = self._form_values(form)
        publish = _field(form, "action") == "publish"
        try:
            post = self.store.create_post(values["title"], values["body"], tags=self._tag_list(values["tags"]),
                                          slug=values["slug"], summary=values["summary"], publish=publish)
        except BlogError as exc:
            status = 409 if isinstance(exc, Conflict) else 400
            return self.html(request, pages.editor_page(self.ctx(request), None, values, error=str(exc)), status)
        notice = "published" if publish else "created"
        return RedirectResponse(f"/admin/edit/{quote(post['slug'], safe='')}?msg={notice}", status_code=303)

    async def edit_form(self, request: Request) -> Response:
        session = self.admin_session(request)
        if isinstance(session, Response):
            return session
        try:
            post = self.store.get_post(request.path_params["slug"])
        except NotFound:
            return self.not_found(request, "There is no post with that address.")
        values = {"title": post["title"], "slug": post["slug"], "tags": ", ".join(post["tags"]),
                  "summary": post["custom_summary"], "body": post["body"]}
        notice = NOTICES.get(request.query_params.get("msg", ""), "")
        return self.html(request, pages.editor_page(self.ctx(request), post, values, notice=notice))

    async def edit(self, request: Request) -> Response:
        session = self.admin_session(request)
        if isinstance(session, Response):
            return session
        slug = request.path_params["slug"]
        form = await request.form(max_part_size=4 * MAX_BODY_CHARS + 1024)
        if not Auth.check_csrf(session, _field(form, "csrf")):
            return self.csrf_failed(request)
        values = self._form_values(form)
        action = _field(form, "action")
        try:
            expected = int(_field(form, "version"))
        except ValueError:
            expected = None
        try:
            post = self.store.update_post(
                slug, title=values["title"], body=values["body"], summary=values["summary"],
                tags=self._tag_list(values["tags"]), new_slug=values["slug"] if values["slug"] and values["slug"] != slug else None,
                expected_version=expected)
            if action == "publish" and post["status"] != "published":
                post = self.store.set_status(post["slug"], "published")
            elif action == "unpublish" and post["status"] != "draft":
                post = self.store.set_status(post["slug"], "draft")
        except NotFound:
            return self.not_found(request, "There is no post with that address.")
        except BlogError as exc:
            try:
                current = self.store.get_post(slug)
            except NotFound:
                return self.not_found(request, "There is no post with that address.")
            error = str(exc)
            if isinstance(exc, Conflict) and "since you loaded" in error:
                error += ". Your text is kept below. Saving again replaces the other version with yours."
            status = 409 if isinstance(exc, Conflict) else 400
            return self.html(request, pages.editor_page(self.ctx(request), current, values, error=error), status)
        notice = {"publish": "published", "unpublish": "unpublished"}.get(action, "saved")
        return RedirectResponse(f"/admin/edit/{quote(post['slug'], safe='')}?msg={notice}", status_code=303)

    async def _post_action(self, request: Request, action: str) -> Response:
        session = self.admin_session(request)
        if isinstance(session, Response):
            return session
        form = await request.form()
        if not Auth.check_csrf(session, _field(form, "csrf")):
            return self.csrf_failed(request)
        slug = request.path_params["slug"]
        try:
            if action == "delete":
                if not self.store.delete_post(slug):
                    raise NotFound(slug)
                notice = "deleted"
            else:
                self.store.set_status(slug, "published" if action == "publish" else "draft")
                notice = "published" if action == "publish" else "unpublished"
        except NotFound:
            return self.not_found(request, "There is no post with that address.")
        return RedirectResponse(f"/admin?msg={notice}", status_code=303)

    async def delete(self, request: Request) -> Response:
        return await self._post_action(request, "delete")

    async def publish(self, request: Request) -> Response:
        return await self._post_action(request, "publish")

    async def unpublish(self, request: Request) -> Response:
        return await self._post_action(request, "unpublish")

    async def preview(self, request: Request) -> Response:
        session = self.admin_session(request)
        if isinstance(session, Response):
            return session
        if not Auth.check_csrf(session, request.headers.get("x-csrf-token")):
            return JSONResponse({"error": "Invalid CSRF token"}, status_code=403)
        text = (await request.body()).decode("utf-8", errors="replace")
        if len(text) > MAX_BODY_CHARS:
            return JSONResponse({"error": "Post is too long"}, status_code=413)
        return HTMLResponse(render_markdown(text))

    async def upload(self, request: Request) -> Response:
        session = self.admin_session(request)
        if isinstance(session, Response):
            return session
        if not Auth.check_csrf(session, request.headers.get("x-csrf-token")):
            return JSONResponse({"error": "Invalid CSRF token"}, status_code=403)
        return await self._save_upload(request)

    async def _save_upload(self, request: Request) -> JSONResponse:
        try:
            form = await request.form(max_files=1, max_fields=4)
            upload = form.get("file")
            if isinstance(upload, str) or upload is None:
                raise BlogError("Send the image in a form field named 'file'")
            name = media.save_image(self.media_dir, await upload.read())
        except BlogError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse({"url": f"/media/{name}", "absolute_url": f"{self.public_base(request)}/media/{name}"}, status_code=201)


def _api_error(message: str, status: int, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status, headers=headers)


def _api(handler):
    """Wrap an API handler: require the bearer token and turn store errors into JSON errors."""

    async def wrapper(self, request: Request) -> Response:
        if not self.auth.check_api_token(request.headers.get("authorization")):
            return _api_error("Missing or invalid API token", 401, {"WWW-Authenticate": 'Bearer realm="blog"'})
        try:
            return await handler(self, request)
        except NotFound as exc:
            return _api_error(str(exc), 404)
        except Conflict as exc:
            return _api_error(str(exc), 409)
        except BlogError as exc:
            return _api_error(str(exc), 400)

    wrapper.__name__ = handler.__name__
    return wrapper


def _body(request_json) -> dict:
    if not isinstance(request_json, dict):
        raise BlogError("The request body must be a JSON object")
    return request_json


def _text(data: dict, key: str, default=None):
    value = data.get(key, default)
    if value is not None and not isinstance(value, str):
        raise BlogError(f"{key} must be a string")
    return value


def _bool(data: dict, key: str, default: bool = False) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise BlogError(f"{key} must be true or false")
    return value


def _tags(data: dict):
    value = data.get("tags")
    if value is not None and (not isinstance(value, list) or not all(isinstance(tag, str) for tag in value)):
        raise BlogError("tags must be a list of strings")
    return value


def _int(request: Request, name: str, default: int) -> int:
    raw = request.query_params.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise BlogError(f"{name} must be an integer") from None


async def _json(request: Request) -> dict:
    try:
        data = await request.json()
    except ValueError:
        raise BlogError("The request body must be valid JSON") from None
    return _body(data)


class _Api:
    """The JSON API under /api/v1, used by tools such as the MCP server. Every call needs the API token."""

    def __init__(self, blog: BlogApp):
        self.blog = blog
        self.store = blog.store
        self.auth = blog.auth

    def with_url(self, request: Request, post: dict) -> dict:
        post["url"] = f"{self.blog.public_base(request)}/post/{quote(post['slug'], safe='')}"
        return post

    @_api
    async def info(self, request: Request) -> Response:
        s = self.blog.settings
        return JSONResponse({"title": s.title, "description": s.description, "public": s.public,
                             "url": self.blog.public_base(request), "posts": self.store.stats()})

    @_api
    async def list_posts(self, request: Request) -> Response:
        result = self.store.list_posts(status=request.query_params.get("status", "all"), tag=request.query_params.get("tag", ""),
                                       limit=_int(request, "limit", 20), offset=_int(request, "offset", 0))
        result["posts"] = [self.with_url(request, p) for p in result["posts"]]
        return JSONResponse(result)

    @_api
    async def create_post(self, request: Request) -> Response:
        data = await _json(request)
        post = self.store.create_post(_text(data, "title", ""), _text(data, "body", ""), tags=_tags(data), slug=_text(data, "slug", ""),
                                      summary=_text(data, "summary", ""), publish=_bool(data, "publish"))
        return JSONResponse(self.with_url(request, post), status_code=201)

    @_api
    async def get_post(self, request: Request) -> Response:
        return JSONResponse(self.with_url(request, self.store.get_post(request.path_params["slug"])))

    @_api
    async def update_post(self, request: Request) -> Response:
        data = await _json(request)
        expected = data.get("expected_version")
        if expected is not None and (not isinstance(expected, int) or isinstance(expected, bool)):
            raise BlogError("expected_version must be an integer")
        post = self.store.update_post(request.path_params["slug"], title=_text(data, "title"), body=_text(data, "body"),
                                      summary=_text(data, "summary"), tags=_tags(data), new_slug=_text(data, "slug"),
                                      expected_version=expected)
        return JSONResponse(self.with_url(request, post))

    @_api
    async def replace_in_post(self, request: Request) -> Response:
        data = await _json(request)
        post = self.store.replace_in_post(request.path_params["slug"], _text(data, "find", ""), _text(data, "replace", ""),
                                          replace_all=_bool(data, "replace_all"))
        return JSONResponse(self.with_url(request, post))

    @_api
    async def publish(self, request: Request) -> Response:
        return JSONResponse(self.with_url(request, self.store.set_status(request.path_params["slug"], "published")))

    @_api
    async def unpublish(self, request: Request) -> Response:
        return JSONResponse(self.with_url(request, self.store.set_status(request.path_params["slug"], "draft")))

    @_api
    async def delete_post(self, request: Request) -> Response:
        slug = request.path_params["slug"]
        if not self.store.delete_post(slug):
            raise NotFound(f"Post '{slug}' not found")
        return JSONResponse({"slug": slug, "deleted": True})

    @_api
    async def search(self, request: Request) -> Response:
        result = self.store.search_posts(request.query_params.get("q", ""), status=request.query_params.get("status", "all"),
                                         limit=_int(request, "limit", 20))
        result["posts"] = [self.with_url(request, p) for p in result["posts"]]
        return JSONResponse(result)

    @_api
    async def tags(self, request: Request) -> Response:
        return JSONResponse(self.store.list_tags(status=request.query_params.get("status", "all")))

    @_api
    async def upload_media(self, request: Request) -> Response:
        return await self.blog._save_upload(request)


def create_app(settings: Settings) -> Starlette:
    """Build the blog as an ASGI application."""
    blog = BlogApp(settings)
    api = _Api(blog)

    async def http_error(request: Request, exc: HTTPException) -> Response:
        if request.url.path.startswith("/api/"):
            return _api_error(exc.detail if exc.status_code != 404 else "Not found", exc.status_code)
        message = {404: "That page does not exist.", 405: "That is not allowed here.", 413: "That upload is too large."}.get(
            exc.status_code, "Something went wrong.")
        title = "Not found" if exc.status_code == 404 else "Error"
        return HTMLResponse(pages.message_page(blog.ctx(request), title, message), status_code=exc.status_code)

    async def server_error(request: Request, exc: Exception) -> Response:
        if request.url.path.startswith("/api/"):
            return _api_error("Internal error", 500)
        return HTMLResponse(pages.message_page(blog.ctx(request), "Error", "Something went wrong."), status_code=500)

    routes = [
        Route("/", blog.home),
        Route("/post/{slug}", blog.post),
        Route("/tag/{tag}", blog.tag),
        Route("/tags", blog.tags),
        Route("/search", blog.search),
        Route("/media/{name}", blog.media_file),
        Route("/healthz", blog.healthz),
        Route("/robots.txt", blog.robots),
        Route("/login", blog.login_form, methods=["GET"]),
        Route("/login", blog.login, methods=["POST"]),
        Route("/logout", blog.logout, methods=["POST"]),
        Route("/admin", blog.dashboard),
        Route("/admin/new", blog.new_form, methods=["GET"]),
        Route("/admin/new", blog.create, methods=["POST"]),
        Route("/admin/edit/{slug}", blog.edit_form, methods=["GET"]),
        Route("/admin/edit/{slug}", blog.edit, methods=["POST"]),
        Route("/admin/delete/{slug}", blog.delete, methods=["POST"]),
        Route("/admin/publish/{slug}", blog.publish, methods=["POST"]),
        Route("/admin/unpublish/{slug}", blog.unpublish, methods=["POST"]),
        Route("/admin/preview", blog.preview, methods=["POST"]),
        Route("/admin/upload", blog.upload, methods=["POST"]),
        Route("/api/v1/info", api.info, methods=["GET"]),
        Route("/api/v1/posts", api.list_posts, methods=["GET"]),
        Route("/api/v1/posts", api.create_post, methods=["POST"]),
        Route("/api/v1/posts/{slug}", api.get_post, methods=["GET"]),
        Route("/api/v1/posts/{slug}", api.update_post, methods=["PATCH"]),
        Route("/api/v1/posts/{slug}", api.delete_post, methods=["DELETE"]),
        Route("/api/v1/posts/{slug}/replace", api.replace_in_post, methods=["POST"]),
        Route("/api/v1/posts/{slug}/publish", api.publish, methods=["POST"]),
        Route("/api/v1/posts/{slug}/unpublish", api.unpublish, methods=["POST"]),
        Route("/api/v1/search", api.search, methods=["GET"]),
        Route("/api/v1/tags", api.tags, methods=["GET"]),
        Route("/api/v1/media", api.upload_media, methods=["POST"]),
        Mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static"),
    ]
    app = Starlette(
        routes=routes,
        middleware=[Middleware(SecurityHeaders, indexable=settings.public), Middleware(BodyLimit, max_bytes=MAX_REQUEST_BYTES)],
        exception_handlers={HTTPException: http_error, Exception: server_error},
    )
    app.state.blog = blog
    return app


__all__ = ["BlogApp", "create_app", "safe_next"]
