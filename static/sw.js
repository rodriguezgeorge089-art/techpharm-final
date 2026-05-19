// static/app.js
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = '<i class="fas fa-check-circle me-2"></i>' + message;
    document.getElementById('toastContainer').appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

document.addEventListener('DOMContentLoaded', function() {
    // Toast message from query string
    const params = new URLSearchParams(window.location.search);
    if(params.get('added') === '1') {
        showToast('Item added to cart!');
    }
    if(params.get('wishlist_added') === '1') {
        showToast('Added to wishlist!');
    }

    // Toast from server-side injected script (toast_script)
    const toastMsg = document.querySelector('meta[name="toast-message"]');
    if (toastMsg) {
        showToast(toastMsg.content);
    }

    // Password toggle
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', function() {
            const input = document.getElementById(this.dataset.target);
            const icon = this.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.replace('fa-eye','fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.replace('fa-eye-slash','fa-eye');
            }
        });
    });
});
