// UI Components Module for Table for Two
// Reusable UI components and interactions

const UIComponents = {
    // Toast notification system
    toast: {
        container: null,
        
        init() {
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.id = 'toast-container';
                this.container.style.cssText = `
                    position: fixed;
                    bottom: 2rem;
                    right: 2rem;
                    z-index: 3000;
                `;
                document.body.appendChild(this.container);
            }
        },

        show(message, type = 'info', duration = 5000) {
            this.init();

            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.style.cssText = `
                background: white;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                display: flex;
                align-items: center;
                gap: 1rem;
                margin-bottom: 1rem;
                transform: translateX(400px);
                transition: transform 0.3s;
                border-left: 4px solid ${
                    type === 'success' ? '#27ae60' :
                    type === 'error' ? '#e74c3c' :
                    type === 'warning' ? '#f39c12' :
                    '#3498db'
                };
            `;

            const icon = {
                success: '✓',
                error: '✕',
                warning: '⚠',
                info: 'ℹ'
            }[type];

            toast.innerHTML = `
                <span style="font-size: 1.2rem;">${icon}</span>
                <span>${message}</span>
                <button onclick="this.parentElement.remove()" style="
                    background: none;
                    border: none;
                    cursor: pointer;
                    margin-left: 1rem;
                    font-size: 1.2rem;
                    color: #999;
                ">✕</button>
            `;

            this.container.appendChild(toast);

            // Trigger animation
            setTimeout(() => {
                toast.style.transform = 'translateX(0)';
            }, 10);

            // Auto remove
            setTimeout(() => {
                toast.style.transform = 'translateX(400px)';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
    },

    // Modal system
    modal: {
        create(options) {
            const {
                title,
                content,
                confirmText = 'Confirm',
                cancelText = 'Cancel',
                onConfirm,
                onCancel,
                className = ''
            } = options;

            const modal = document.createElement('div');
            modal.className = `modal ${className}`;
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 2000;
            `;

            modal.innerHTML = `
                <div class="modal-content" style="
                    background: white;
                    border-radius: 16px;
                    max-width: 500px;
                    width: 90%;
                    padding: 2rem;
                    max-height: 90vh;
                    overflow-y: auto;
                ">
                    <div class="modal-header" style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 1.5rem;
                    ">
                        <h2 style="margin: 0; font-size: 1.5rem;">${title}</h2>
                        <button class="modal-close" style="
                            background: none;
                            border: none;
                            font-size: 1.5rem;
                            cursor: pointer;
                            color: #999;
                        ">&times;</button>
                    </div>
                    <div class="modal-body" style="margin-bottom: 1.5rem;">
                        ${content}
                    </div>
                    <div class="modal-footer" style="
                        display: flex;
                        justify-content: flex-end;
                        gap: 1rem;
                    ">
                        <button class="btn btn-secondary modal-cancel">${cancelText}</button>
                        <button class="btn btn-primary modal-confirm">${confirmText}</button>
                    </div>
                </div>
            `;

            // Event handlers
            const closeModal = () => {
                modal.style.opacity = '0';
                setTimeout(() => modal.remove(), 300);
            };

            modal.querySelector('.modal-close').onclick = closeModal;
            modal.querySelector('.modal-cancel').onclick = () => {
                if (onCancel) onCancel();
                closeModal();
            };
            modal.querySelector('.modal-confirm').onclick = () => {
                if (onConfirm) onConfirm();
                closeModal();
            };

            // Click outside to close
            modal.onclick = (e) => {
                if (e.target === modal) closeModal();
            };

            document.body.appendChild(modal);

            // Fade in animation
            modal.style.opacity = '0';
            modal.style.transition = 'opacity 0.3s';
            setTimeout(() => {
                modal.style.opacity = '1';
            }, 10);

            return modal;
        },

        confirm(message, onConfirm) {
            return this.create({
                title: 'Confirm',
                content: `<p>${message}</p>`,
                onConfirm
            });
        },

        alert(message, title = 'Alert') {
            return this.create({
                title,
                content: `<p>${message}</p>`,
                cancelText: 'OK',
                confirmText: '',
                onConfirm: null
            });
        }
    },

    // Loading overlay
    loading: {
        overlay: null,

        show(message = 'Loading...') {
            if (!this.overlay) {
                this.overlay = document.createElement('div');
                this.overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(255, 255, 255, 0.9);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    z-index: 3000;
                `;
            }

            this.overlay.innerHTML = `
                <div class="loading-spinner" style="
                    width: 50px;
                    height: 50px;
                    border: 3px solid #f3f3f3;
                    border-top: 3px solid #e74c3c;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                "></div>
                <p style="margin-top: 1rem; color: #666;">${message}</p>
            `;

            document.body.appendChild(this.overlay);
        },

        hide() {
            if (this.overlay) {
                this.overlay.remove();
            }
        }
    },

    // Dropdown menu
    dropdown: {
        create(trigger, items) {
            const dropdown = document.createElement('div');
            dropdown.className = 'dropdown-menu';
            dropdown.style.cssText = `
                position: absolute;
                top: 100%;
                right: 0;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                min-width: 200px;
                margin-top: 0.5rem;
                display: none;
                z-index: 1000;
            `;

            items.forEach(item => {
                if (item.divider) {
                    const divider = document.createElement('div');
                    divider.style.cssText = `
                        height: 1px;
                        background: #e0e0e0;
                        margin: 0.5rem 0;
                    `;
                    dropdown.appendChild(divider);
                } else {
                    const menuItem = document.createElement('a');
                    menuItem.href = item.href || '#';
                    menuItem.textContent = item.label;
                    menuItem.style.cssText = `
                        display: block;
                        padding: 0.75rem 1rem;
                        color: #333;
                        text-decoration: none;
                        transition: background 0.2s;
                    `;
                    menuItem.onmouseover = () => {
                        menuItem.style.background = '#f8f9fa';
                    };
                    menuItem.onmouseout = () => {
                        menuItem.style.background = 'none';
                    };
                    if (item.onclick) {
                        menuItem.onclick = (e) => {
                            e.preventDefault();
                            item.onclick();
                            dropdown.style.display = 'none';
                        };
                    }
                    dropdown.appendChild(menuItem);
                }
            });

            // Position relative to trigger
            const container = trigger.parentElement;
            container.style.position = 'relative';
            container.appendChild(dropdown);

            // Toggle on click
            trigger.onclick = (e) => {
                e.stopPropagation();
                dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
            };

            // Close on outside click
            document.addEventListener('click', () => {
                dropdown.style.display = 'none';
            });

            return dropdown;
        }
    },

    // Form validation
    form: {
        validate(form) {
            const errors = {};
            const inputs = form.querySelectorAll('[required], [pattern], [type="email"]');

            inputs.forEach(input => {
                const value = input.value.trim();
                const name = input.name;

                // Required validation
                if (input.hasAttribute('required') && !value) {
                    errors[name] = `${this.getFieldLabel(input)} is required`;
                }

                // Email validation
                else if (input.type === 'email' && value && !Utils.validateEmail(value)) {
                    errors[name] = 'Please enter a valid email address';
                }

                // Pattern validation
                else if (input.hasAttribute('pattern') && value) {
                    const pattern = new RegExp(input.getAttribute('pattern'));
                    if (!pattern.test(value)) {
                        errors[name] = input.getAttribute('data-error') || 'Invalid format';
                    }
                }

                // Custom validation
                else if (input.hasAttribute('data-validate')) {
                    const validator = window[input.getAttribute('data-validate')];
                    if (validator && typeof validator === 'function') {
                        const error = validator(value);
                        if (error) errors[name] = error;
                    }
                }
            });

            return { valid: Object.keys(errors).length === 0, errors };
        },

        showErrors(form, errors) {
            // Clear existing errors
            form.querySelectorAll('.error-message').forEach(el => el.remove());
            form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));

            // Show new errors
            Object.entries(errors).forEach(([name, message]) => {
                const input = form.querySelector(`[name="${name}"]`);
                if (input) {
                    input.classList.add('error');
                    const errorEl = document.createElement('div');
                    errorEl.className = 'error-message';
                    errorEl.style.cssText = `
                        color: #e74c3c;
                        font-size: 0.875rem;
                        margin-top: 0.25rem;
                    `;
                    errorEl.textContent = message;
                    input.parentElement.appendChild(errorEl);
                }
            });
        },

        getFieldLabel(input) {
            const label = input.closest('label') || 
                         document.querySelector(`label[for="${input.id}"]`);
            return label ? label.textContent.replace('*', '').trim() : 
                   input.placeholder || input.name;
        }
    },

    // Image preview
    imagePreview: {
        create(input, previewEl) {
            input.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file && file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        previewEl.innerHTML = `<img src="${e.target.result}" style="
                            max-width: 100%;
                            max-height: 200px;
                            border-radius: 8px;
                        ">`;
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    },

    // Autocomplete
    autocomplete: {
        create(input, options) {
            const {
                source,
                minLength = 2,
                onSelect
            } = options;

            const container = document.createElement('div');
            container.style.cssText = `
                position: absolute;
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                max-height: 200px;
                overflow-y: auto;
                display: none;
                z-index: 1000;
                width: 100%;
            `;

            input.parentElement.style.position = 'relative';
            input.parentElement.appendChild(container);

            let currentFocus = -1;

            input.addEventListener('input', async (e) => {
                const value = e.target.value;
                if (value.length < minLength) {
                    container.style.display = 'none';
                    return;
                }

                const items = typeof source === 'function' ? 
                    await source(value) : 
                    source.filter(item => 
                        item.toLowerCase().includes(value.toLowerCase())
                    );

                if (items.length === 0) {
                    container.style.display = 'none';
                    return;
                }

                container.innerHTML = '';
                items.forEach((item, index) => {
                    const div = document.createElement('div');
                    div.style.cssText = `
                        padding: 0.75rem 1rem;
                        cursor: pointer;
                    `;
                    div.textContent = typeof item === 'object' ? item.label : item;
                    div.addEventListener('click', () => {
                        input.value = typeof item === 'object' ? item.label : item;
                        container.style.display = 'none';
                        if (onSelect) onSelect(item);
                    });
                    div.addEventListener('mouseover', () => {
                        currentFocus = index;
                        updateFocus();
                    });
                    container.appendChild(div);
                });

                container.style.display = 'block';
            });

            const updateFocus = () => {
                const items = container.children;
                for (let i = 0; i < items.length; i++) {
                    items[i].style.background = i === currentFocus ? '#f8f9fa' : 'white';
                }
            };

            input.addEventListener('keydown', (e) => {
                const items = container.children;
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    currentFocus = Math.min(currentFocus + 1, items.length - 1);
                    updateFocus();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    currentFocus = Math.max(currentFocus - 1, 0);
                    updateFocus();
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    if (currentFocus > -1 && items[currentFocus]) {
                        items[currentFocus].click();
                    }
                } else if (e.key === 'Escape') {
                    container.style.display = 'none';
                }
            });

            document.addEventListener('click', (e) => {
                if (!input.contains(e.target) && !container.contains(e.target)) {
                    container.style.display = 'none';
                }
            });
        }
    },

    // Lazy loading for images
    lazyLoad: {
        init() {
            const images = document.querySelectorAll('img[data-src]');
            
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            img.src = img.dataset.src;
                            img.onload = () => img.classList.add('loaded');
                            img.removeAttribute('data-src');
                            imageObserver.unobserve(img);
                        }
                    });
                });

                images.forEach(img => imageObserver.observe(img));
            } else {
                // Fallback for older browsers
                images.forEach(img => {
                    img.src = img.dataset.src;
                    img.onload = () => img.classList.add('loaded');
                    img.removeAttribute('data-src');
                });
            }
        }
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIComponents;
}

// For use in HTML files
if (typeof window !== 'undefined') {
    window.UIComponents = UIComponents;
    // Alias for common components
    window.showToast = UIComponents.toast.show.bind(UIComponents.toast);
    window.showModal = UIComponents.modal.create.bind(UIComponents.modal);
    window.showLoading = UIComponents.loading.show.bind(UIComponents.loading);
    window.hideLoading = UIComponents.loading.hide.bind(UIComponents.loading);
}
