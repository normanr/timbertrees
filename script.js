document.addEventListener('DOMContentLoaded', (event) => {
  document.addEventListener('click', (event) => {
    let searchable = event.target.closest('[data-searchable]')?.dataset.searchable.split(' ');
    if (!searchable) {
      return;
    };
    let srcRect = event.target.getBoundingClientRect();
    document.querySelectorAll('.expose, .found').forEach(e => {
      e.classList.remove('expose');
      e.classList.remove('found');
    });
    if (document.getElementById('content').classList.contains('searching')) {
      document.getElementById('content').classList.remove('searching');
      let dstRect = event.target.getBoundingClientRect();
      let dy = dstRect.top - srcRect.top;
      window.scrollBy(0, dy);
      return;
    };
    document.getElementById('content').classList.add('searching');
    selectors = searchable.map(id => `[data-searchable~=${JSON.stringify(id)}]`);
    document.querySelectorAll(selectors.join(', ')).forEach(e => {
      e.classList.add('found');
      e = e.parentElement.closest('.card');
      while (!e.classList.contains('searching')) {
        e.classList.add('expose');
        e = e.parentElement.closest('.card');
      }
    });
    let dstRect = event.target.getBoundingClientRect();
    let dy = dstRect.top - srcRect.top;
    window.scrollBy(0, dy);
  });
});
