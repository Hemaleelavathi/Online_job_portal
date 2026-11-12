/* CareerConnect progressive enhancement utilities */
document.addEventListener('DOMContentLoaded', () => {
    // Fallback mobile navbar toggle if Bootstrap Collapse JS is unavailable
    document.querySelectorAll('.navbar-toggler[data-bs-target]').forEach((toggler) => {
        const targetSelector = toggler.getAttribute('data-bs-target');
        const collapseEl = targetSelector ? document.querySelector(targetSelector) : null;
        if (!collapseEl) {
            return;
        }

        const bootstrapCollapseAvailable = Boolean(window.bootstrap && window.bootstrap.Collapse);
        if (!bootstrapCollapseAvailable) {
            const setExpanded = (isOpen) => {
                collapseEl.classList.toggle('show', isOpen);
                toggler.classList.toggle('collapsed', !isOpen);
                toggler.setAttribute('aria-expanded', String(isOpen));
            };

            toggler.addEventListener('click', () => {
                setExpanded(!collapseEl.classList.contains('show'));
            });

            collapseEl.querySelectorAll('.nav-link').forEach((link) => {
                link.addEventListener('click', () => {
                    if (window.innerWidth < 768) {
                        setExpanded(false);
                    }
                });
            });

            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape' && collapseEl.classList.contains('show')) {
                    setExpanded(false);
                }
            });
        }
    });

    // Password show/hide toggles
    document.querySelectorAll('.cc-password-toggle').forEach((toggleBtn) => {
        toggleBtn.addEventListener('click', () => {
            const targetId = toggleBtn.getAttribute('data-target');
            const input = targetId ? document.getElementById(targetId) : null;
            if (!input) {
                return;
            }
            const showPlaintext = input.type === 'password';
            input.type = showPlaintext ? 'text' : 'password';
            toggleBtn.setAttribute('aria-pressed', String(showPlaintext));
            toggleBtn.setAttribute('aria-label', showPlaintext ? 'Hide password' : 'Show password');
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                icon.classList.toggle('bi-eye', !showPlaintext);
                icon.classList.toggle('bi-eye-slash', showPlaintext);
            }
        });
    });

    // Live file-selection hint for PDF resume inputs
    document.querySelectorAll('input[type="file"][data-file-hint]').forEach((fileInput) => {
        fileInput.addEventListener('change', () => {
            const hintId = fileInput.getAttribute('data-file-hint');
            const hintEl = hintId ? document.getElementById(hintId) : null;
            if (!hintEl) {
                return;
            }
            const file = fileInput.files && fileInput.files[0];
            if (!file) {
                hintEl.textContent = '';
                return;
            }
            const isPdf = file.name.toLowerCase().endsWith('.pdf');
            const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
            if (!isPdf) {
                hintEl.className = 'form-text text-danger fw-medium';
                hintEl.textContent = `Selected "${file.name}" is not a .pdf file.`;
            } else if (file.size > 5 * 1024 * 1024) {
                hintEl.className = 'form-text text-danger fw-medium';
                hintEl.textContent = `Selected "${file.name}" (${sizeMb} MB) exceeds the 5 MB limit.`;
            } else {
                hintEl.className = 'form-text text-success fw-medium';
                hintEl.textContent = `Ready to upload: ${file.name} (${sizeMb} MB)`;
            }
        });
    });

    // Auto-dismiss non-error flash messages cleanly
    if (window.bootstrap && window.bootstrap.Alert) {
        document.querySelectorAll('.alert:not(.alert-danger)').forEach((alertEl) => {
            window.setTimeout(() => {
                if (document.body.contains(alertEl)) {
                    window.bootstrap.Alert.getOrCreateInstance(alertEl).close();
                }
            }, 6000);
        });
    }
});
