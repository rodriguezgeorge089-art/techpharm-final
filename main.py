{% extends "admin_base.html" %}
{% block title %}Dashboard – {{ pharmacy_name }}{% endblock %}
{% block admin_content %}

<div class="top-bar">
    <div>
        <h4 class="fw-bold mb-0" style="color: var(--deep-blue);">Welcome back, {{ session.user_name or 'Admin' }}!</h4>
        <p class="text-muted mb-0">Here's what's happening today.</p>
    </div>
</div>

<div class="row g-4 mb-4">
    <div class="col-md-3">
        <div class="card border-0 shadow-sm rounded-4 p-4">
            <div class="d-flex align-items-center justify-content-between">
                <div>
                    <p class="text-muted mb-0">Total Sales</p>
                    <h3 class="fw-bold">KSh {{ total_sales }}</h3>
                </div>
                <div class="stat-icon bg-success bg-opacity-10 text-success rounded-3 p-3">
                    <i class="fas fa-dollar-sign fa-2x"></i>
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card border-0 shadow-sm rounded-4 p-4">
            <div class="d-flex align-items-center justify-content-between">
                <div>
                    <p class="text-muted mb-0">Orders</p>
                    <h3 class="fw-bold">{{ total_orders }}</h3>
                </div>
                <div class="stat-icon bg-warning bg-opacity-10 text-warning rounded-3 p-3">
                    <i class="fas fa-shopping-bag fa-2x"></i>
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card border-0 shadow-sm rounded-4 p-4">
            <div class="d-flex align-items-center justify-content-between">
                <div>
                    <p class="text-muted mb-0">Products</p>
                    <h3 class="fw-bold">{{ total_products }}</h3>
                </div>
                <div class="stat-icon bg-primary bg-opacity-10 text-primary rounded-3 p-3">
                    <i class="fas fa-pills fa-2x"></i>
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card border-0 shadow-sm rounded-4 p-4">
            <div class="d-flex align-items-center justify-content-between">
                <div>
                    <p class="text-muted mb-0">Customers</p>
                    <h3 class="fw-bold">{{ total_customers }}</h3>
                </div>
                <div class="stat-icon bg-danger bg-opacity-10 text-danger rounded-3 p-3">
                    <i class="fas fa-users fa-2x"></i>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="card border-0 shadow-sm rounded-4 p-4 mb-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h5 class="fw-bold mb-0"><i class="far fa-clock me-2"></i>Recent Orders</h5>
        <a href="/admin/orders" class="btn btn-sm btn-outline-primary rounded-pill">View All</a>
    </div>
    <div class="table-responsive">
        <table class="table align-middle">
            <thead class="table-dark">
                <tr>
                    <th>Order ID</th>
                    <th>Customer</th>
                    <th>Total</th>
                    <th>Status</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
                {{ recent_orders | safe }}
            </tbody>
        </table>
    </div>
</div>

<div class="row g-4">
    <div class="col-md-4">
        <a href="/admin/add-product" class="text-decoration-none">
            <div class="card border-0 shadow-sm rounded-4 p-4 text-center hover-lift">
                <i class="fas fa-plus-circle fa-3x mb-3" style="color: var(--gold);"></i>
                <h6 class="fw-bold">Add New Product</h6>
            </div>
        </a>
    </div>
    <div class="col-md-4">
        <a href="/admin/orders" class="text-decoration-none">
            <div class="card border-0 shadow-sm rounded-4 p-4 text-center hover-lift">
                <i class="fas fa-list-check fa-3x mb-3" style="color: var(--gold);"></i>
                <h6 class="fw-bold">Manage Orders</h6>
            </div>
        </a>
    </div>
    <div class="col-md-4">
        <a href="/admin/export-orders" class="text-decoration-none">
            <div class="card border-0 shadow-sm rounded-4 p-4 text-center hover-lift">
                <i class="fas fa-file-csv fa-3x mb-3" style="color: var(--gold);"></i>
                <h6 class="fw-bold">Export CSV</h6>
            </div>
        </a>
    </div>
</div>

<style>
    .hover-lift { transition: transform 0.3s, box-shadow 0.3s; }
    .hover-lift:hover { transform: translateY(-5px); box-shadow: 0 15px 30px rgba(10,61,98,0.15); }
</style>
{% endblock %}
