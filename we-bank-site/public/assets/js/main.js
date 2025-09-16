(() => {
  const toggleButton = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.site-nav');
  if (!toggleButton || !nav) return;
  toggleButton.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('open');
    toggleButton.setAttribute('aria-expanded', String(isOpen));
  });
})();

