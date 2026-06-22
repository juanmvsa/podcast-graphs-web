// dom utility functions.

// query selectors with type safety.
export function $(selector: string): HTMLElement | null {
  return document.querySelector(selector);
}

export function $$(selector: string): NodeListOf<HTMLElement> {
  return document.querySelectorAll(selector);
}

// escape html to prevent xss.
export function escapeHTML(str: string): string {
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

// create element with attributes and children.
export function createElement<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs?: Record<string, string>,
  children?: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (attrs) {
    Object.entries(attrs).forEach(([key, value]) => {
      if (key.startsWith('data-')) {
        el.dataset[key.slice(5)] = value;
      } else if (key === 'className') {
        el.className = value;
      } else {
        el.setAttribute(key, value);
      }
    });
  }
  if (children) {
    children.forEach((child) => {
      if (typeof child === 'string') {
        el.appendChild(document.createTextNode(child));
      } else {
        el.appendChild(child);
      }
    });
  }
  return el;
}

// debounce function for search input.
export function debounce<T extends (...args: Parameters<T>) => void>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

// smooth scroll to top.
export function scrollToTop(): void {
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// toggle class helper.
export function toggleClass(el: HTMLElement | null, className: string, force?: boolean): void {
  if (el) el.classList.toggle(className, force);
}

// set aria attribute helper.
export function setAria(el: HTMLElement | null, attr: string, value: string): void {
  if (el) el.setAttribute(`aria-${attr}`, value);
}
