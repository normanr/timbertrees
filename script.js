document.addEventListener('DOMContentLoaded', (event) => {
  let content = document.getElementById('content');

  function updateContent(searchable, categories) {
    document.querySelectorAll('.expose, .found').forEach(e => {
      e.classList.remove('expose');
      e.classList.remove('found');
    });
    if (!searchable) {
      return;
    };
    let suffix = (categories || []).map(c => `[data-category~=${JSON.stringify(c)}]`);
    let selectors = searchable.map(id => `[data-searchable~=${JSON.stringify(id)}]` + suffix);
    document.querySelectorAll(selectors.join(', ')).forEach(e => {
      e.classList.add('found');
      e = e.parentElement.closest('.card');
      while (e) {
        e.classList.add('expose');
        e = e.parentElement.closest('.card');
      }
    });
  }

  function searchableClick(event) {
    let srcRect = event.target.getBoundingClientRect();
    if (content.dataset.searching) {
      delete content.dataset.searching;
      delete content.dataset.categories;
      updateContent(null);
    } else {
      let searchable = event.target.closest('[data-searchable]')?.dataset.searchable.split(' ');
      content.dataset.searching = searchable.join(' ');
      updateContent(searchable);
    }
    let dstRect = event.target.getBoundingClientRect();
    let dy = dstRect.top - srcRect.top;
    window.scrollBy(0, dy);
  }

  function toggleClick(event) {
    if (!content.dataset.categories) {
      content.dataset.categories = "producer";
    } else if (content.dataset.categories == "producer") {
      content.dataset.categories = "consumer";
    } else if (content.dataset.categories == "consumer") {
      delete content.dataset.categories;
    }
    updateContent(content.dataset.searching.split(' '), content.dataset.categories?.split(' '))
  }

  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-searchable]')) {
      searchableClick(event);
    };
    if (event.target.closest('#toggle')) {
      toggleClick(event);
    };
  });
});
