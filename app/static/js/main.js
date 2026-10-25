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
})();