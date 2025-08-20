document.addEventListener('DOMContentLoaded', () => {
    // Initialize GitHub-style outline
    initGithubOutline();
    
    // 检查当前主题模式并添加相应的类
    const darkModeEnabled = document.documentElement.getAttribute('data-color-mode') === 'dark';
    if (darkModeEnabled) {
        document.body.classList.add('theme-dark');
    } else {
        document.body.classList.add('theme-light');
    }
    
    // 监听主题变化
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'data-color-mode') {
                const darkMode = document.documentElement.getAttribute('data-color-mode') === 'dark';
                if (darkMode) {
                    document.body.classList.remove('theme-light');
                    document.body.classList.add('theme-dark');
                } else {
                    document.body.classList.remove('theme-dark');
                    document.body.classList.add('theme-light');
                }
            }
        });
    });
    
    observer.observe(document.documentElement, { attributes: true });
    
    // 调整大纲侧栏位置以与post-header对齐
    adjustOutlinePosition();
    window.addEventListener('resize', adjustOutlinePosition);
    window.addEventListener('scroll', adjustOutlinePosition);
    
    // 自动显示目录结构，无需点击按钮
    setTimeout(() => {
        showOutline();
        // 更新TOC按钮状态
        const tocButton = document.getElementById('toc-toggle');
        if (tocButton) {
            tocButton.setAttribute('aria-expanded', 'true');
            tocButton.classList.add('selected');
        }
    }, 300); // 延迟一点时间确保DOM已加载完成
});

// TOC button click handler
function clickToc() {
    const outline = document.getElementById('gh-outline');
    if (outline.style.display === 'block') {
        hideOutline();
    } else {
        showOutline();
    }
    
    // 阻止事件冒泡，防止点击TOC按钮同时触发document的点击事件
    event.stopPropagation();
    
    // 设置aria-expanded属性
    const tocButton = document.getElementById('toc-toggle');
    if (tocButton) {
        const isExpanded = outline.style.display === 'block';
        tocButton.setAttribute('aria-expanded', isExpanded);
        if (isExpanded) {
            tocButton.classList.add('selected');
        } else {
            tocButton.classList.remove('selected');
        }
    }
    
    return false;
}

function showOutline() {
    const outline = document.getElementById('gh-outline');
    if (!outline) return;
    
    // 确保显示大纲
    outline.style.display = 'block';
    
    // 短暂延迟以确保CSS过渡效果正常工作
    setTimeout(() => {
        outline.classList.add('visible');
    }, 10);
    
    // Initialize outline content if not already done
    populateOutline();
    
    // 不再添加点击外部区域关闭目录的功能
    // 仅保留关闭按钮的功能
}

function hideOutline() {
    const outline = document.getElementById('gh-outline');
    if (!outline) return;
    
    outline.classList.remove('visible');
    
    // 等待过渡效果结束后隐藏元素
    setTimeout(() => {
        outline.style.display = 'none';
    }, 200); // 与CSS过渡时间匹配
    
    // 只有当关闭按钮被点击时才会调用此函数，不再需要移除其他事件监听器
}

function handleEscapeKey(e) {
    if (e.key === 'Escape') {
        hideOutline();
    }
}

function handleClickOutside(e) {
    const outline = document.getElementById('gh-outline');
    // 如果点击的不是大纲区域内的元素且不是TOC按钮，则关闭大纲
    if (outline && !outline.contains(e.target) && e.target.id !== 'toc-toggle' && !e.target.closest('#toc-toggle')) {
        hideOutline();
    }
}

function initGithubOutline() {
    // Get the markdown content
    const markdownBody = document.querySelector('.markdown-body');
    if (!markdownBody) return;
    
    // Get all headings
    const headings = markdownBody.querySelectorAll('h1, h2, h3, h4, h5, h6');
    if (headings.length === 0) return;
    
    // Ensure all headings have IDs
    headings.forEach((heading) => {
        if (!heading.id) {
            heading.id = createSlug(heading.textContent);
        }
    });
    
    // Set up close button handler
    const closeButton = document.getElementById('close-outline');
    if (closeButton) {
        closeButton.addEventListener('click', hideOutline);
    }
    
    // Set up scroll handling for active state
    window.addEventListener('scroll', debounce(updateActiveOutlineItem, 100));
}

function populateOutline() {
    const outlineContent = document.getElementById('gh-outline-content');
    if (!outlineContent || outlineContent.querySelector('.gh-outline-list')) return;
    
    const markdownBody = document.querySelector('.markdown-body');
    if (!markdownBody) return;
    
    const headings = markdownBody.querySelectorAll('h1, h2, h3, h4, h5, h6');
    
    // 如果没有标题，就不显示大纲
    if (headings.length === 0) {
        hideOutline();
        return;
    }
    
    // 创建导航容器
    const nav = document.createElement('nav');
    nav.className = 'gh-outline-content-nav';
    
    // 创建列表
    const list = document.createElement('ul');
    list.className = 'gh-outline-list';
    
    headings.forEach((heading) => {
        // 确保标题有id
        if (!heading.id) {
            heading.id = createSlug(heading.textContent);
        }
        
        // 获取标题级别 (但不再用于调整字体大小)
        const level = parseInt(heading.tagName.substring(1));
        
        // 创建列表项
        const listItem = document.createElement('li');
        
        // 创建链接 - 根据标题级别设置不同的缩进
        const link = document.createElement('a');
        // 添加标题级别的类名，确保与CSS选择器匹配
        link.className = `h${level}`; 
        link.href = `#${heading.id}`;
        link.textContent = heading.textContent;
        link.addEventListener('click', (e) => {
            e.preventDefault();
            heading.scrollIntoView({behavior: 'smooth'});
            window.history.pushState(null, null, `#${heading.id}`);
            // 移除隐藏大纲的功能，使目录始终保持显示
        });
        
        listItem.appendChild(link);
        list.appendChild(listItem);
    });
    
    nav.appendChild(list);
    outlineContent.appendChild(nav);
    
    // 更新活跃状态
    updateActiveOutlineItem();
}

// 定位大纲，使其与post-header同高
function adjustOutlinePosition() {
    const outline = document.getElementById('gh-outline');
    const postHeader = document.getElementById('post-header');
    const fileBox = document.getElementById('file-pytest');
    
    if (!outline || !postHeader || !fileBox) return;
    
    // 获取post-header的位置和高度信息
    const headerRect = postHeader.getBoundingClientRect();
    // 获取文章容器的位置信息
    const fileBoxRect = fileBox.getBoundingClientRect();
    
    // 设置大纲位置，使其与post-header顶部对齐
    outline.style.top = `${headerRect.top}px`;
    
    // 明确设置左侧位置为文章div右侧+16px
    outline.style.left = `${fileBoxRect.right + 16}px`;
    // 清除right属性，避免冲突
    outline.style.right = 'auto';
    
    // 设置最大高度，以避免超出页面底部
    const maxHeight = window.innerHeight - headerRect.top - 16;
    outline.style.maxHeight = `${maxHeight}px`;
    
    // 添加调试信息，以帮助排查问题
    console.log('文章右边界:', fileBoxRect.right);
    console.log('TOC位置:', outline.style.left);
}

function updateActiveOutlineItem() {
    const outlineItems = document.querySelectorAll('.gh-outline-list li a');
    if (outlineItems.length === 0) return;
    
    const markdownBody = document.querySelector('.markdown-body');
    if (!markdownBody) return;
    
    const headings = markdownBody.querySelectorAll('h1, h2, h3, h4, h5, h6');
    
    let currentActiveItem = null;
    let lastVisibleHeadingTop = -Infinity;
    
    // Find the heading that is currently in view
    headings.forEach((heading, index) => {
        const rect = heading.getBoundingClientRect();
        
        // Consider a heading as "in view" if its top is visible or just passed the top
        if (rect.top <= 100 && rect.top > lastVisibleHeadingTop) {
            lastVisibleHeadingTop = rect.top;
            if (index < outlineItems.length) {
                currentActiveItem = outlineItems[index];
            }
        }
    });
    
    // If no heading is in view, use the first one
    if (!currentActiveItem && outlineItems.length > 0) {
        currentActiveItem = outlineItems[0];
    }
    
    // Update active class
    outlineItems.forEach(item => item.classList.remove('active'));
    if (currentActiveItem) {
        currentActiveItem.classList.add('active');
    }
}

// Helper function to create slug for heading IDs
function createSlug(text) {
    return text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/[\s_-]+/g, '-')
        .replace(/^-+|-+$/g, '');
}

// Debounce function to limit scroll event handling
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const later = () => {
            timeout = null;
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
