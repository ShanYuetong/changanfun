/* 长安玩乐指南 - Service Worker
 *
 * 设计原则（与项目整体一致：轻量、可降级、不引入外部依赖）：
 *
 * 1. 只缓存「应用外壳」：HTML 页面、CSS、JS、图标、manifest。
 *    不缓存 /api/ 接口数据 —— 活动列表必须始终看到最新内容，
 *    缓存接口会导致用户看到过期活动，这在信息类产品里是严重问题。
 *
 * 2. 策略：
 *    - 页面导航：网络优先（network-first），失败时回退到缓存的离线页。
 *      这样在线时永远是最新内容，离线时才用缓存兜底。
 *    - 静态资源（CSS/JS/图标）：缓存优先（cache-first），
 *      因为文件名固定、内容稳定，缓存优先能显著加快二次加载。
 *
 * 3. Service Worker 本身不做任何业务逻辑。即使它完全失效、
 *    或浏览器不支持，网站依然可用——这正是渐进增强的含义。
 */

const CACHE_VERSION = "changan-v1";
const CACHE_NAME = `${CACHE_VERSION}-shell`;

/* 预缓存的应用外壳。路径与项目实际结构保持一致。 */
const SHELL_ASSETS = [
  "/",
  "/static/css/style.css",
  "/static/js/main.js",
  "/static/manifest.json",
  "/static/icons/icon.svg",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/favicon.svg",
  "/static/offline.html",
];

/* 安装：预缓存外壳。任一资源失败不应导致整个安装失败，
   否则后续更新会一直卡住，所以用 allSettled 逐个处理。 */
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) =>
        Promise.allSettled(SHELL_ASSETS.map((url) => cache.add(new Request(url, { cache: "reload" }))))
      )
      .then(() => self.skipWaiting())
  );
});

/* 激活：清理旧版本缓存，并立即接管页面。 */
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter((name) => name.startsWith("changan-") && name !== CACHE_NAME)
            .map((name) => caches.delete(name))
        )
      )
      .then(() => self.clients.claim())
  );
});

/* 请求拦截。 */
self.addEventListener("fetch", (event) => {
  const request = event.request;

  /* 只处理 GET。POST 等一律放行给网络（本项目暂无写操作，留作扩展）。 */
  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);

  /* 只处理同源请求，不触碰第三方资源。 */
  if (url.origin !== self.location.origin) {
    return;
  }

  /* 接口数据永不缓存：活动信息必须实时。 */
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  /* 页面导航：网络优先，离线时回退。 */
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          /* 成功则顺手更新缓存中的首页副本。 */
          if (response && response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put("/", copy));
          }
          return response;
        })
        .catch(async () => {
          const cache = await caches.open(CACHE_NAME);
          const cached = (await cache.match(request)) || (await cache.match("/"));
          if (cached) {
            return cached;
          }
          /* 连首页缓存都没有时，返回离线提示页。 */
          const offline = await cache.match("/static/offline.html");
          if (offline) {
            return offline;
          }
          return new Response("当前处于离线状态，且没有可用的缓存页面。", {
            status: 503,
            headers: { "Content-Type": "text/plain; charset=utf-8" },
          });
        })
    );
    return;
  }

  /* 静态资源：缓存优先，未命中时请求网络并回填缓存。 */
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request)
        .then((response) => {
          /* 只缓存成功的同源响应。 */
          if (response && response.ok && response.type === "basic") {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => {
          /* 静态资源加载失败时返回 404，不抛异常打断页面。 */
          return new Response("", { status: 404, statusText: "Not Found" });
        });
    })
  );
});