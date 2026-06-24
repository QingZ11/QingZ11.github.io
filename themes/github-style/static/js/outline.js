document.addEventListener('DOMContentLoaded', () => {
  // Check if we're on a post page
  const markdownBody = document.querySelector('.markdown-body');
  if (!markdownBody) return;
  
  // Get all headings
  const headings = markdownBody.querySelectorAll('h1, h2, h3, h4, h5, h6');
  if (headings.length === 0) return;

  // Get the outline container
  const outlineContent = document.getElementById('outline-content');
  if (!outlineContent) return;
  
  // Add the 'has-outline' class to body
  document.body.classList.add('has-outline');
  
  // Create outline items
  headings.forEach((heading) => {
    // Get heading level (h1, h2, etc.)
    const level = parseInt(heading.tagName.substring(1));
    
    // Create or ensure ID for the heading
    if (!heading.id) {
      heading.id = createSlug(heading.textContent);
    }
    
    // Create outline item
    const outlineItem = document.createElement('a');
    outlineItem.href = `#${heading.id}`;
    outlineItem.className = `outline-item outline-h${level}`;
    outlineItem.textContent = heading.textContent;
    outlineItem.addEventListener('click', (e) => {
      e.preventDefault();
      heading.scrollIntoView({behavior: 'smooth'});
      window.history.pushState(null, null, `#${heading.id}`);
    });
    
    outlineContent.appendChild(outlineItem);
  });

  // Initialize active state
  updateActiveOutlineItem();
  
  // Update active item on scroll
  window.addEventListener('scroll', debounce(updateActiveOutlineItem, 50));
  
  // Helper functions
  function createSlug(text) {
    return text
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_-]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  function updateActiveOutlineItem() {
    const outlineItems = document.querySelectorAll('.outline-item');
    let currentActiveItem = null;
    let lastVisibleHeadingTop = -Infinity;
    
    // Find the heading that is currently in view
    headings.forEach((heading, index) => {
      const rect = heading.getBoundingClientRect();
      
      // Consider a heading as "in view" if its top is visible or just passed the top
      if (rect.top <= 100 && rect.top > lastVisibleHeadingTop) {
        lastVisibleHeadingTop = rect.top;
        currentActiveItem = outlineItems[index];
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
});
