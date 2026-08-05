/* CoolQBot 功能图鉴 · 交互脚本 */
(function () {
  "use strict";

  /* ---------- 顶部导航 ---------- */
  var header = document.querySelector("[data-header]");
  var menuToggle = document.querySelector("[data-menu-toggle]");
  var navigation = document.querySelector("[data-navigation]");

  function onHeaderScroll() {
    header.classList.toggle("is-scrolled", window.scrollY > 8);
  }
  window.addEventListener("scroll", onHeaderScroll, { passive: true });
  onHeaderScroll();

  menuToggle.addEventListener("click", function () {
    var open = navigation.classList.toggle("is-open");
    menuToggle.setAttribute("aria-expanded", String(open));
    menuToggle.setAttribute(
      "aria-label",
      open ? "关闭导航菜单" : "打开导航菜单",
    );
  });

  navigation.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      navigation.classList.remove("is-open");
      menuToggle.setAttribute("aria-expanded", "false");
    });
  });

  /* ---------- 功能搜索 ---------- */
  var searchInput = document.querySelector("[data-search-input]");
  var cards = Array.prototype.slice.call(document.querySelectorAll(".fx-card"));
  var groups = Array.prototype.slice.call(
    document.querySelectorAll(".fx-group"),
  );
  var resultCount = document.querySelector("[data-result-count]");
  var emptyState = document.querySelector("[data-empty]");
  var total = cards.length;

  function applyFilter() {
    var query = searchInput.value.trim().toLowerCase();
    var visible = 0;

    cards.forEach(function (card) {
      var haystack = (
        card.getAttribute("data-search") +
        " " +
        card.textContent
      ).toLowerCase();
      var hit = !query || haystack.indexOf(query) !== -1;
      card.hidden = !hit;
      if (hit) visible++;
    });

    // 隐藏没有可见卡片的分组
    groups.forEach(function (group) {
      var hasVisible = Array.prototype.some.call(
        group.querySelectorAll(".fx-card"),
        function (card) {
          return !card.hidden;
        },
      );
      group.hidden = !hasVisible;
    });

    emptyState.hidden = visible !== 0;
    resultCount.textContent = query
      ? "匹配 " + visible + " / " + total + " 项功能"
      : "共 " + total + " 项功能";
  }

  if (searchInput) {
    searchInput.addEventListener("input", applyFilter);
  }

  /* ---------- 侧边目录 scroll-spy ---------- */
  var asideLinks = Array.prototype.slice.call(
    document.querySelectorAll("[data-aside-nav] .aside-link"),
  );

  if ("IntersectionObserver" in window && asideLinks.length) {
    var linkById = {};
    asideLinks.forEach(function (link) {
      linkById[link.getAttribute("href").slice(1)] = link;
    });

    var spy = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            asideLinks.forEach(function (l) {
              l.classList.remove("is-active");
            });
            var link = linkById[entry.target.id];
            if (link) link.classList.add("is-active");
          }
        });
      },
      { rootMargin: "-20% 0px -70% 0px" },
    );
    groups.forEach(function (group) {
      spy.observe(group);
    });
  }

  /* ---------- 复制命令 ---------- */
  function legacyCopy(text) {
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy")
          ? resolve()
          : reject(new Error("copy failed"));
      } catch (err) {
        reject(err);
      }
      document.body.removeChild(ta);
    });
  }

  function copyText(text) {
    if (navigator.clipboard) {
      return navigator.clipboard.writeText(text).catch(function () {
        return legacyCopy(text);
      });
    }
    return legacyCopy(text);
  }

  document.querySelectorAll("[data-copy]").forEach(function (button) {
    button.addEventListener("click", function () {
      var label = button.querySelector("em");
      copyText(button.getAttribute("data-copy")).then(showCopied, showCopied);
      function showCopied() {
        button.classList.add("is-copied");
        if (label) label.textContent = "已复制";
        setTimeout(function () {
          button.classList.remove("is-copied");
          if (label) label.textContent = "复制";
        }, 1600);
      }
    });
  });

  /* ---------- 入场动画 ---------- */
  var revealElements = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var revealObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -6% 0px" },
    );
    revealElements.forEach(function (el) {
      revealObserver.observe(el);
    });
  } else {
    revealElements.forEach(function (el) {
      el.classList.add("is-in");
    });
  }

  /* ---------- 回到顶部 ---------- */
  var backTop = document.querySelector("[data-back-top]");
  if (backTop) {
    backTop.hidden = false;
    window.addEventListener(
      "scroll",
      function () {
        backTop.classList.toggle("is-visible", window.scrollY > 600);
      },
      { passive: true },
    );
    backTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  /* ---------- 页脚年份 ---------- */
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });
})();
