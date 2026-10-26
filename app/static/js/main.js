/* 长安玩乐指南 - 轻量交互增强
 *
 * 设计原则：页面的搜索、分类、详情等核心功能完全依赖 GET 查询参数与
 * 服务端渲染，即使 JavaScript 被禁用或加载失败也能正常使用。
 * 本文件只做「锦上添花」的体验优化，不承担任何核心逻辑。
 */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    // ---- 1. 「清空输入」按钮：只清空搜索框，不直接提交 ----
    var clearButton = document.querySelector(".js-clear-search");
    var searchInput = document.getElementById("search-input");

    if (clearButton && searchInput) {
      clearButton.addEventListener("click", function () {
        searchInput.value = "";
        searchInput.focus();
      });
    }

    // ---- 2. 按 "/" 快速聚焦搜索框（输入框内不触发） ----
    document.addEventListener("keydown", function (event) {
      if (event.key !== "/" || !searchInput) {
        return;
      }
      var active = document.activeElement;
      var tagName = active ? active.tagName : "";
      var isTyping =
        tagName === "INPUT" || tagName === "TEXTAREA" || active.isContentEditable;

      if (!isTyping) {
        event.preventDefault();
        searchInput.focus();
      }
    });

    // ---- 3. 从详情页返回时，若浏览器未恢复滚动位置，则回到列表区 ----
    // 仅在明确带有 #events 锚点且页面未自动滚动时执行，避免干扰正常浏览。
    if (window.location.hash === "#events" && window.scrollY === 0) {
      var target = document.getElementById("events");
      if (target) {
        target.scrollIntoView({ block: "start" });
      }
    }
  });

  // ---- 4. 注册 Service Worker（PWA） ----
  // 仅在支持时注册；注册失败不影响页面任何功能。
  // 放在 load 之后，避免与首屏渲染抢占资源。
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      // 必须用根路径 /sw.js：从 /static/sw.js 注册时，默认作用域会被限制在
      // /static/ 下，Service Worker 就无法接管页面导航请求。
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {
        /* 注册失败（如非 HTTPS 环境、浏览器限制）时静默忽略，不影响页面功能 */
      });
    });
  }

  // ---- 5. 「添加到主屏幕」提示 ----
  // 浏览器触发 beforeinstallprompt 时才有机会展示；已安装或用户拒绝过则不再打扰。
  var DISMISS_KEY = "changan-install-dismissed";
  var deferredPrompt = null;
  var hint = document.getElementById("install-hint");
  var acceptBtn = document.getElementById("install-accept");
  var dismissBtn = document.getElementById("install-dismiss");

  function hideHint() {
    if (hint) {
      hint.hidden = true;
    }
  }

  function hasDismissed() {
    try {
      return window.localStorage.getItem(DISMISS_KEY) === "1";
    } catch (error) {
      // 隐私模式下 localStorage 可能抛异常，此时按「已拒绝」处理，不打扰用户
      return true;
    }
  }

  function rememberDismiss() {
    try {
      window.localStorage.setItem(DISMISS_KEY, "1");
    } catch (error) {
      /* 存不下就算了，不影响功能 */
    }
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    // 必须阻止默认的迷你提示条，才能用我们自己样式一致的提示
    event.preventDefault();
    deferredPrompt = event;

    if (hint && !hasDismissed()) {
      hint.hidden = false;
    }
  });

  if (acceptBtn) {
    acceptBtn.addEventListener("click", function () {
      hideHint();
      if (!deferredPrompt) {
        return;
      }
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then(function (choice) {
        if (choice && choice.outcome === "accepted") {
          rememberDismiss();
        }
        deferredPrompt = null;
      });
    });
  }

  if (dismissBtn) {
    dismissBtn.addEventListener("click", function () {
      hideHint();
      rememberDismiss();
    });
  }

  // 已安装（standalone 模式）时不再提示
  window.addEventListener("appinstalled", function () {
    hidePrompt();
    rememberDismiss();
  });

  function hidePrompt() {
    hideHint();
    deferredPrompt = null;
  }

  if (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) {
    hideHint();
  }
})();