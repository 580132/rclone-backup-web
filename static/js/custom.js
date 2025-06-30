// 自定义JavaScript功能

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeAnimations();
    initializeTooltips();
    initializeNotifications();
    initializeThemeEffects();
});

// 初始化动画效果
function initializeAnimations() {
    // 为所有卡片添加悬停效果
    const cards = document.querySelectorAll('.glass-card, .stat-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });

    // 滚动时显示元素
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // 观察所有需要动画的元素
    const animatedElements = document.querySelectorAll('.glass-card, .stat-card, .page-header');
    animatedElements.forEach(el => {
        observer.observe(el);
    });
}

// 初始化工具提示
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            customClass: 'tooltip-custom'
        });
    });
}

// 通知系统
function initializeNotifications() {
    window.showNotification = function(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        const icon = getNotificationIcon(type);
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi ${icon} me-2"></i>
                <span>${message}</span>
                <button type="button" class="btn-close ms-auto" onclick="hideNotification(this)"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // 显示通知
        setTimeout(() => notification.classList.add('show'), 100);
        
        // 自动隐藏
        setTimeout(() => hideNotification(notification), duration);
        
        return notification;
    };
    
    window.hideNotification = function(element) {
        const notification = element.closest ? element.closest('.notification') : element;
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    };
}

// 获取通知图标
function getNotificationIcon(type) {
    const icons = {
        success: 'bi-check-circle',
        error: 'bi-exclamation-triangle',
        warning: 'bi-exclamation-triangle',
        info: 'bi-info-circle'
    };
    return icons[type] || icons.info;
}

// 主题效果
function initializeThemeEffects() {
    // 鼠标跟随效果
    let mouseX = 0, mouseY = 0;
    let cursorX = 0, cursorY = 0;
    
    document.addEventListener('mousemove', function(e) {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });
    
    // 平滑的鼠标跟随光标
    function animateCursor() {
        const diffX = mouseX - cursorX;
        const diffY = mouseY - cursorY;
        
        cursorX += diffX * 0.1;
        cursorY += diffY * 0.1;
        
        // 更新背景渐变位置
        document.body.style.background = `
            radial-gradient(600px at ${cursorX}px ${cursorY}px, rgba(0, 0, 0, 0.03), transparent 40%),
            linear-gradient(135deg, #ffffff 0%, #f8f9fa 50%, #ffffff 100%)
        `;
        
        requestAnimationFrame(animateCursor);
    }
    
    animateCursor();
}

// 加载状态管理
window.showLoading = function(element, text = '加载中...') {
    const originalContent = element.innerHTML;
    element.dataset.originalContent = originalContent;
    element.innerHTML = `
        <span class="loading-spinner me-2"></span>
        ${text}
    `;
    element.disabled = true;
};

window.hideLoading = function(element) {
    if (element.dataset.originalContent) {
        element.innerHTML = element.dataset.originalContent;
        delete element.dataset.originalContent;
    }
    element.disabled = false;
};

// 确认对话框增强
window.confirmAction = function(message, onConfirm, onCancel) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content modal-content-modern">
                <div class="modal-header modal-header-modern">
                    <h5 class="modal-title fw-bold">
                        <i class="bi bi-question-circle text-warning me-2"></i>确认操作
                    </h5>
                </div>
                <div class="modal-body modal-body-modern">
                    <p class="mb-0">${message}</p>
                </div>
                <div class="modal-footer modal-footer-modern">
                    <button type="button" class="btn btn-gradient-secondary" data-bs-dismiss="modal">
                        <i class="bi bi-x-lg me-2"></i>取消
                    </button>
                    <button type="button" class="btn btn-gradient-danger" id="confirmBtn">
                        <i class="bi bi-check-lg me-2"></i>确认
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const bsModal = new bootstrap.Modal(modal);
    
    modal.querySelector('#confirmBtn').addEventListener('click', function() {
        bsModal.hide();
        if (onConfirm) onConfirm();
    });
    
    modal.addEventListener('hidden.bs.modal', function() {
        document.body.removeChild(modal);
        if (onCancel) onCancel();
    });
    
    bsModal.show();
};

// 文件大小格式化
window.formatFileSize = function(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 时间格式化
window.formatDuration = function(seconds) {
    if (!seconds) return '-';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
};

// 复制到剪贴板
window.copyToClipboard = function(text, successMessage = '已复制到剪贴板') {
    navigator.clipboard.writeText(text).then(function() {
        showNotification(successMessage, 'success');
    }).catch(function() {
        // 降级方案
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showNotification(successMessage, 'success');
    });
};

// 表格排序功能
window.initTableSort = function(tableSelector) {
    const table = document.querySelector(tableSelector);
    if (!table) return;
    
    const headers = table.querySelectorAll('th[data-sort]');
    headers.forEach(header => {
        header.style.cursor = 'pointer';
        header.innerHTML += ' <i class="bi bi-arrow-down-up ms-1"></i>';
        
        header.addEventListener('click', function() {
            const column = this.dataset.sort;
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            const isAscending = !this.classList.contains('sort-asc');
            
            // 清除其他列的排序状态
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            
            // 设置当前列的排序状态
            this.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
            
            // 排序行
            rows.sort((a, b) => {
                const aVal = a.querySelector(`[data-value="${column}"]`)?.dataset.value || 
                           a.cells[Array.from(this.parentNode.children).indexOf(this)].textContent;
                const bVal = b.querySelector(`[data-value="${column}"]`)?.dataset.value || 
                           b.cells[Array.from(this.parentNode.children).indexOf(this)].textContent;
                
                if (isAscending) {
                    return aVal.localeCompare(bVal, undefined, { numeric: true });
                } else {
                    return bVal.localeCompare(aVal, undefined, { numeric: true });
                }
            });
            
            // 重新插入排序后的行
            rows.forEach(row => tbody.appendChild(row));
        });
    });
};

// 自动保存功能
window.autoSave = function(formSelector, saveCallback, interval = 30000) {
    const form = document.querySelector(formSelector);
    if (!form) return;
    
    let saveTimer;
    let hasChanges = false;
    
    // 监听表单变化
    form.addEventListener('input', function() {
        hasChanges = true;
        clearTimeout(saveTimer);
        saveTimer = setTimeout(() => {
            if (hasChanges && saveCallback) {
                saveCallback(new FormData(form));
                hasChanges = false;
                showNotification('已自动保存', 'success', 2000);
            }
        }, interval);
    });
    
    // 页面卸载前保存
    window.addEventListener('beforeunload', function() {
        if (hasChanges && saveCallback) {
            saveCallback(new FormData(form));
        }
    });
};
