let lastScrollY = window.scrollY;
const navbar = document.querySelector('.navbar');


const hamburger = document.getElementById('hamburger');
const navLinks = document.querySelector('.nav-links');

if (hamburger && navLinks) {
  hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('open');
    navLinks.classList.toggle('open');
  });

  navLinks.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      hamburger.classList.remove('open');
      navLinks.classList.remove('open');
    });
  });
}

window.addEventListener('scroll', () => {
  const currentScroll = window.scrollY;
  const isMobile = window.innerWidth <= 768;

  if (isMobile) {
    
    navbar.style.top = '0';
    navbar.style.position = 'fixed';
    if (currentScroll > 10) {
      navbar.classList.add('navbar-visible');
    } else {
      navbar.classList.remove('navbar-visible');
    }
  } else {
   
    if (currentScroll === 0) {
      navbar.classList.remove('navbar-visible');
      navbar.style.top = '0';
    } else if (currentScroll < lastScrollY) {
      navbar.style.top = '0';
      navbar.classList.add('navbar-visible');
    } else {
      navbar.style.top = '-100px';
      navbar.classList.remove('navbar-visible');
    }
  }

  lastScrollY = currentScroll;
});
