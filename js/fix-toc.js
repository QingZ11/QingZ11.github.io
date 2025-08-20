// 在页面加载后执行
document.addEventListener('DOMContentLoaded', function() {
  // 为TOC按钮添加点击事件，清除所有可能的背景和边框样式
  const tocButton = document.getElementById('toc-toggle');
  if (tocButton) {
    tocButton.addEventListener('click', function(event) {
      // 阻止事件冒泡
      event.stopPropagation();
      // 确保按钮没有背景
      this.style.background = 'transparent';
      this.style.boxShadow = 'none';
      this.style.outline = 'none';
      this.style.border = 'none';
      
      // 返回false以防止默认行为
      return false;
    });
  }
  
  // 实现点击文章中的标题后，TOC中对应标题高亮显示功能
  function initTocHighlight() {
    // 为正文中的所有标题添加点击事件
    const articleHeadings = document.querySelectorAll('.markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4, .markdown-body h5, .markdown-body h6');
    articleHeadings.forEach(heading => {
      heading.addEventListener('click', function() {
        highlightTocItem(heading.id);
      });
    });
    
    // 监听hash变化，用于处理直接访问带有锚点的URL
    window.addEventListener('hashchange', function() {
      const hash = window.location.hash.substring(1);
      if (hash) {
        highlightTocItem(hash);
      }
    });
    
    // 初始检查URL中是否包含锚点
    if (window.location.hash) {
      const hash = window.location.hash.substring(1);
      highlightTocItem(hash);
    }
    
    // 监听滚动事件，同步高亮TOC
    window.addEventListener('scroll', debounce(syncTocWithScroll, 100));
    
    // 初始同步TOC高亮状态
    syncTocWithScroll();
  }
  
  // 根据ID高亮对应的TOC项
  function highlightTocItem(id) {
    if (!id) return;
    
    // 移除所有TOC项的高亮状态
    const tocLinks = document.querySelectorAll('.gh-outline-list li a');
    tocLinks.forEach(link => link.classList.remove('active'));
    
    // 添加高亮状态到对应的TOC项
    const targetLink = document.querySelector(`.gh-outline-list li a[href="#${id}"]`);
    if (targetLink) {
      targetLink.classList.add('active');
    }
  }
  
  // 根据滚动位置同步TOC高亮
  function syncTocWithScroll() {
    const headings = document.querySelectorAll('.markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4, .markdown-body h5, .markdown-body h6');
    if (headings.length === 0) return;
    
    let currentHeadingId = '';
    let closestDistance = Number.MAX_VALUE;
    const scrollPosition = window.scrollY + 100; // 添加偏移量，使其在标题接近顶部时就高亮
    
    // 找到最接近当前滚动位置的标题
    headings.forEach(heading => {
      const distance = Math.abs(heading.offsetTop - scrollPosition);
      if (distance < closestDistance && heading.offsetTop <= scrollPosition) {
        closestDistance = distance;
        currentHeadingId = heading.id;
      }
    });
    
    // 高亮对应的TOC项
    if (currentHeadingId) {
      highlightTocItem(currentHeadingId);
    }
  }
  
  // 防抖函数，避免滚动事件过于频繁触发
  function debounce(func, wait) {
    let timeout;
    return function() {
      const context = this;
      const args = arguments;
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        func.apply(context, args);
      }, wait);
    };
  }
  
  // 当页面完全加载后初始化TOC高亮功能
  // 使用setTimeout确保DOM已完全加载
  setTimeout(() => {
    if (document.querySelector('.gh-outline')) {
      initTocHighlight();
    }
  }, 500);
});
