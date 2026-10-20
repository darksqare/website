/* projects page: auto-discovers the .html files in /projects/ (via nginx's JSON
   directory listing at /api/projects/) and runs the sync button.
   A page's title is just its file name without ".html". */
(function () {
  var list = document.getElementById("project-list");
  var btn = document.getElementById("sync-btn");
  var out = document.getElementById("sync-status");
  if (!list) return;

  function render(files) {
    list.textContent = "";
    if (!files.length) {
      var empty = document.createElement("li");
      empty.textContent = "nothing here yet";
      list.appendChild(empty);
      return;
    }
    files.forEach(function (name) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = "projects/" + encodeURIComponent(name);
      a.textContent = name.replace(/\.html$/i, "");
      li.appendChild(a);
      list.appendChild(li);
    });
  }

  function load() {
    fetch("/api/projects/", { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (entries) {
        var files = entries
          .filter(function (e) {
            return e.type === "file" && /\.html$/i.test(e.name) && e.name.charAt(0) !== ".";
          })
          .map(function (e) { return e.name; })
          .sort(function (a, b) { return a.toLowerCase() < b.toLowerCase() ? -1 : 1; });
        render(files);
      })
      .catch(function () { /* listing not available: keep the list written in the HTML */ });
  }

  function summary(d) {
    var parts = [];
    if (d.new.length) parts.push(d.new.length + " new");
    if (d.updated.length) parts.push(d.updated.length + " updated");
    parts.push(d.unchanged + " unchanged");
    if (d.skipped.length) parts.push(d.skipped.length + " skipped");
    return "synced: " + parts.join(", ");
  }

  if (btn) {
    btn.addEventListener("click", function () {
      btn.disabled = true;
      out.textContent = "syncing...";
      fetch("/api/sync", { method: "POST" })
        .then(function (r) {
          return r.json().catch(function () { return { ok: false, error: "http " + r.status }; });
        })
        .then(function (d) {
          if (d.ok) { out.textContent = summary(d); load(); }
          else { out.textContent = "sync failed: " + (d.error || "unknown error"); }
        })
        .catch(function () { out.textContent = "sync failed: server not reachable"; })
        .then(function () { btn.disabled = false; });
    });
  }

  load();
})();
