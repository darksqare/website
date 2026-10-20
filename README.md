# darkdev.boo

Personal static site (terminal-style, no build step, no dependencies) served by nginx,
plus a tiny optional service behind the **[sync]** button on the projects page.

```
.
├── index.html, about.html, friends.html, projects.html, 404.html
├── projects/            # project pages, auto-listed on projects.html
├── assets/
│   ├── css/style.css
│   ├── js/uptime.js     # header uptime counter (edit START date)
│   ├── js/projects.js   # project list auto-discovery + sync button
│   └── icons/
├── nginx/
│   ├── darkdev.boo.conf # server block
│   └── redirects.conf   # short links / redirects (included by the server block)
└── sync/
    ├── sync_server.py        # stdlib-only service behind the [sync] button
    ├── darkdev-sync.service  # systemd unit
    └── nginx-snippet.conf    # the /api/ locations, if you keep your own nginx config
```

## Preview locally

```sh
python3 -m http.server 8000
# open http://localhost:8000
```

The sync button and project auto-discovery need nginx (`/api/*`), so they only work on the server.

## Deploy

```sh
git clone https://github.com/darksqare/website /var/www/folder1
chown -R www-data:www-data /var/www/folder1
find /var/www/folder1 -type d -exec chmod 755 {} \;
find /var/www/folder1 -type f -exec chmod 644 {} \;

cp /var/www/folder1/nginx/darkdev.boo.conf /etc/nginx/conf.d/darkdev.boo.conf
rm -f /etc/nginx/sites-enabled/default      # only if the default site is enabled
nginx -t && systemctl reload nginx
```

Update later with:

```sh
cd /var/www/folder1 && git pull
```

If git complains about "dubious ownership" (repo owned by `www-data`, pulled as root):
`git config --global --add safe.directory /var/www/folder1`

### Sync service (only needed for the `[sync]` button)

```sh
mkdir -p /opt/darkdev-sync
cp /var/www/folder1/sync/sync_server.py /opt/darkdev-sync/
cp /var/www/folder1/sync/darkdev-sync.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now darkdev-sync
```

- Copies `*.html` from `/mnt/shared/info_ora/html` into `projects/`: new files are added,
  existing ones are replaced only if the source is newer and different. It never deletes anything.
- Paths are the `Environment=` lines in `darkdev-sync.service`.
- It runs as `www-data`, which must be able to read the source folder and write `projects/`.
- After editing `sync_server.py`: `systemctl restart darkdev-sync`.

## Editing

- **Links / buttons:** `index.html`
- **Redirects:** `nginx/redirects.conf` (then reload nginx)
- **Uptime start date:** `assets/js/uptime.js`
- **Projects:** drop any `.html` into `projects/`. The file name (without `.html`) is the title.

## Notes

- Files synced into `projects/` on the server show up as untracked in `git status`.
  Commit the ones you want to keep, or leave them untracked.
- Redirect gotcha: don't write `location = /index.html { return 301 /; }`. nginx serves `/` by
  internally jumping to `/index.html`, which loops forever. `redirects.conf` uses an `if` on
  `$request_uri` instead.
