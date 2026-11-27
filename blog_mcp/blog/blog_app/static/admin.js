// Editor behavior: live preview, image upload (button, paste, drag and drop), Ctrl/Cmd+S,
// unsaved-changes warning, and confirmation prompts. No libraries; served from /static
// so the page's Content-Security-Policy can forbid inline script.
(function () {
  "use strict";

  // Ask before any form marked data-confirm (delete buttons).
  document.addEventListener("submit", function (event) {
    var message = event.target.getAttribute && event.target.getAttribute("data-confirm");
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });

  var form = document.getElementById("editor");
  if (!form) {
    return;
  }
  var csrf = form.getAttribute("data-csrf");
  var body = document.getElementById("body");
  var preview = document.getElementById("preview");
  var status = document.getElementById("upload-status");
  var fileInput = document.getElementById("image-file");
  var dirty = false;
  var submitting = false;

  // --- live preview: the server renders it with the same renderer the blog uses ---
  var timer = null;
  var latest = 0;
  function renderPreview() {
    var ticket = ++latest;
    fetch("/admin/preview", {
      method: "POST",
      headers: { "Content-Type": "text/plain; charset=utf-8", "X-CSRF-Token": csrf },
      credentials: "same-origin",
      body: body.value
    }).then(function (response) {
      return response.ok ? response.text() : "";
    }).then(function (html) {
      if (ticket === latest) {
        preview.innerHTML = html;
      }
    }).catch(function () { /* keep the last good preview */ });
  }
  function schedulePreview() {
    window.clearTimeout(timer);
    timer = window.setTimeout(renderPreview, 250);
  }
  body.addEventListener("input", function () { dirty = true; schedulePreview(); });
  form.addEventListener("input", function () { dirty = true; });
  renderPreview();

  // --- images ---
  function insertAtCursor(text) {
    var start = body.selectionStart;
    var end = body.selectionEnd;
    body.value = body.value.slice(0, start) + text + body.value.slice(end);
    body.selectionStart = body.selectionEnd = start + text.length;
    body.focus();
    dirty = true;
    schedulePreview();
  }
  function upload(file) {
    if (!file || file.type.indexOf("image/") !== 0) {
      status.textContent = "That is not an image.";
      return;
    }
    status.textContent = "Uploading…";
    var data = new FormData();
    data.append("file", file);
    fetch("/admin/upload", {
      method: "POST",
      headers: { "X-CSRF-Token": csrf },
      credentials: "same-origin",
      body: data
    }).then(function (response) {
      return response.json().then(function (json) { return { ok: response.ok, json: json }; });
    }).then(function (result) {
      if (!result.ok) {
        status.textContent = result.json.error || "Upload failed.";
        return;
      }
      var alt = file.name.replace(/\.[^.]+$/, "").replace(/[\[\]]/g, "");
      insertAtCursor("![" + alt + "](" + result.json.url + ")\n");
      status.textContent = "Image added.";
    }).catch(function () {
      status.textContent = "Upload failed.";
    });
  }
  fileInput.addEventListener("change", function () {
    if (fileInput.files.length) { upload(fileInput.files[0]); }
    fileInput.value = "";
  });
  body.addEventListener("paste", function (event) {
    var items = (event.clipboardData && event.clipboardData.files) || [];
    if (items.length && items[0].type.indexOf("image/") === 0) {
      event.preventDefault();
      upload(items[0]);
    }
  });
  body.addEventListener("dragover", function (event) {
    event.preventDefault();
    body.parentNode.classList.add("dragging");
  });
  body.addEventListener("dragleave", function () { body.parentNode.classList.remove("dragging"); });
  body.addEventListener("drop", function (event) {
    body.parentNode.classList.remove("dragging");
    var files = (event.dataTransfer && event.dataTransfer.files) || [];
    if (files.length) {
      event.preventDefault();
      upload(files[0]);
    }
  });

  // --- save shortcut and leaving with unsaved edits ---
  document.addEventListener("keydown", function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      submitting = true;
      var save = form.querySelector('button[name="action"][value="save"]');
      if (save) { save.click(); } else { form.submit(); }
    }
  });
  form.addEventListener("submit", function () { submitting = true; });
  window.addEventListener("beforeunload", function (event) {
    if (dirty && !submitting) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
})();
