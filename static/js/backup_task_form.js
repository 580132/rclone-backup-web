// 备份任务表单的JavaScript代码

// 存储配置选择处理
let selectedStorageConfigs = new Map(); // 存储选中的配置和路径

// 目录浏览器相关功能
let currentBrowsePath = '/';

function openStorageConfigModal() {
    // 显示弹窗
    const modal = new bootstrap.Modal(document.getElementById('storageConfigModal'));
    modal.show();

    // 恢复之前的选择状态
    selectedStorageConfigs.forEach((remotePath, configId) => {
        const checkbox = document.getElementById(`modal_storage_config_${configId}`);
        const pathInput = document.getElementById(`modal_remote_path_${configId}`);
        const pathContainer = document.getElementById(`modal_path_container_${configId}`);

        if (checkbox) {
            checkbox.checked = true;
            pathContainer.style.display = 'block';
            pathInput.value = remotePath;
        }
    });
}

function toggleModalStorageConfig(configId) {
    const checkbox = document.getElementById(`modal_storage_config_${configId}`);
    const pathContainer = document.getElementById(`modal_path_container_${configId}`);
    const pathInput = document.getElementById(`modal_remote_path_${configId}`);

    if (checkbox.checked) {
        pathContainer.style.display = 'block';
        pathInput.focus();
    } else {
        pathContainer.style.display = 'none';
        pathInput.value = '';
    }
}

function confirmStorageSelection() {
    // 清空之前的选择
    selectedStorageConfigs.clear();

    // 获取所有选中的配置
    const checkedBoxes = document.querySelectorAll('.storage-modal-checkbox:checked');

    if (checkedBoxes.length === 0) {
        alert('请至少选择一个存储配置');
        return;
    }

    // 验证每个选中的配置都有远程路径
    let allValid = true;
    checkedBoxes.forEach(checkbox => {
        const configId = checkbox.value;
        const pathInput = document.getElementById(`modal_remote_path_${configId}`);
        const remotePath = pathInput.value.trim();

        if (!remotePath) {
            allValid = false;
            pathInput.focus();
            return;
        }

        selectedStorageConfigs.set(configId, remotePath);
    });

    if (!allValid) {
        alert('请为所有选中的存储配置设置远程路径');
        return;
    }

    // 更新主界面显示
    updateStorageConfigDisplay();

    // 关闭弹窗
    const modal = bootstrap.Modal.getInstance(document.getElementById('storageConfigModal'));
    modal.hide();
}

function updateStorageConfigDisplay() {
    const container = document.getElementById('selectedStorageConfigs');
    const tagsContainer = document.getElementById('selectedStorageTags');

    // 清空现有标签
    tagsContainer.innerHTML = '';

    if (selectedStorageConfigs.size === 0) {
        container.style.display = 'none';
        return;
    }

    // 显示容器
    container.style.display = 'block';

    // 为每个选中的配置创建标签
    selectedStorageConfigs.forEach((remotePath, configId) => {
        const configOption = document.querySelector(`[data-config-id="${configId}"]`);
        const configName = configOption.querySelector('label div div').textContent;
        const configType = configOption.querySelector('label div small').textContent;

        const tag = document.createElement('div');
        tag.className = 'badge bg-primary d-flex align-items-center';
        tag.innerHTML = `
            <div class="me-2">
                <div class="fw-medium">${configName}</div>
                <small>${remotePath}</small>
            </div>
            <button type="button" class="btn-close btn-close-white btn-sm" onclick="removeStorageConfig('${configId}')"></button>
        `;

        tagsContainer.appendChild(tag);
    });
}

function removeStorageConfig(configId) {
    selectedStorageConfigs.delete(configId);
    updateStorageConfigDisplay();
}

// 将选中的存储配置数据添加到表单中
function addStorageConfigsToForm() {
    // 清除之前添加的隐藏字段
    const existingFields = document.querySelectorAll('input[name^="storage_config_"], input[name^="remote_path_"]');
    existingFields.forEach(field => field.remove());

    // 为每个选中的存储配置添加隐藏字段
    const form = document.querySelector('form');
    selectedStorageConfigs.forEach((remotePath, configId) => {
        // 添加存储配置ID
        const configInput = document.createElement('input');
        configInput.type = 'hidden';
        configInput.name = `storage_config_${configId}`;
        configInput.value = configId;
        form.appendChild(configInput);

        // 添加远程路径
        const pathInput = document.createElement('input');
        pathInput.type = 'hidden';
        pathInput.name = `remote_path_${configId}`;
        pathInput.value = remotePath;
        form.appendChild(pathInput);
    });
}

// 表单验证函数
function validateForm() {
    const name = document.getElementById('task_name').value.trim();
    const sourcePath = document.getElementById('source_path').value.trim();

    if (!name) {
        alert('请输入任务名称');
        return false;
    }

    if (!sourcePath) {
        alert('请选择源路径');
        return false;
    }

    // 验证存储配置选择
    if (selectedStorageConfigs.size === 0) {
        alert('请至少选择一个存储配置');
        return false;
    }

    // 在表单提交前，将选中的存储配置数据添加到表单中
    addStorageConfigsToForm();

    return true;
}

// 切换压缩选项显示
function toggleCompression() {
    const enabled = document.getElementById('compression_enabled').checked;
    const options = document.getElementById('compression_options');
    options.style.display = enabled ? 'block' : 'none';
}

// 切换加密选项显示
function toggleEncryption() {
    const enabled = document.getElementById('encryption_enabled').checked;
    const options = document.getElementById('encryption_options');
    options.style.display = enabled ? 'block' : 'none';
}

// 显示目录浏览器
function showDirectoryBrowser() {
    const modal = new bootstrap.Modal(document.getElementById('directoryBrowserModal'));
    modal.show();
    loadDirectory('/');
}

// 显示Cron帮助
function showCronHelper() {
    const modal = new bootstrap.Modal(document.getElementById('cronHelpModal'));
    modal.show();
}

// 加载目录
function loadDirectory(path) {
    currentBrowsePath = path;
    document.getElementById('currentPath').textContent = path;
    
    // 显示加载状态
    document.getElementById('directoryTree').innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
        </div>
    `;

    fetch(`/api/browse-directory?path=${encodeURIComponent(path)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                document.getElementById('directoryTree').innerHTML =
                    `<div class="alert alert-warning">${data.error}</div>`;
            } else {
                renderDirectoryTree(data.directories, data.files, path);
            }
        })
        .catch(error => {
            console.error('Directory loading error:', error);
            document.getElementById('directoryTree').innerHTML =
                '<div class="alert alert-danger">加载目录失败</div>';
        });
}

// 渲染目录树
function renderDirectoryTree(directories, files, currentPath) {
    let html = '<div class="directory-tree">';

    // 添加返回上级目录按钮（如果不是根目录）
    if (currentPath !== '/') {
        const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
        html += `
            <div class="directory-item" onclick="loadDirectory('${escapeHtml(parentPath)}')">
                <i class="bi bi-arrow-up"></i> 返回上级目录
            </div>
        `;
    }

    // 添加目录
    directories.forEach(dir => {
        html += `
            <div class="directory-item" onclick="loadDirectory('${escapeHtml(dir.path)}')">
                <i class="bi bi-folder"></i> ${escapeHtml(dir.name)}
            </div>
        `;
    });

    // 添加文件（仅显示，不可选择）
    files.forEach(file => {
        html += `
            <div class="directory-item file-item">
                <i class="bi bi-file"></i> ${escapeHtml(file.name)}
            </div>
        `;
    });

    html += '</div>';
    document.getElementById('directoryTree').innerHTML = html;
}

// 选择当前路径
function selectCurrentPath() {
    document.getElementById('source_path').value = currentBrowsePath;
    const modal = bootstrap.Modal.getInstance(document.getElementById('directoryBrowserModal'));
    modal.hide();
}

// HTML转义函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 初始化调度设置
function initializeScheduleSettings() {
    // 监听定时类型变化
    const scheduleTypes = document.querySelectorAll('input[name="schedule_type"]');
    scheduleTypes.forEach(radio => {
        radio.addEventListener('change', handleScheduleTypeChange);
    });

    // 监听高级设置切换
    const advancedCheckbox = document.getElementById('show_advanced_cron');
    if (advancedCheckbox) {
        advancedCheckbox.addEventListener('change', toggleAdvancedCron);
    }

    // 监听各种设置变化
    document.getElementById('daily_time')?.addEventListener('change', updateCronExpression);
    document.getElementById('weekly_time')?.addEventListener('change', updateCronExpression);
    document.getElementById('monthly_day')?.addEventListener('change', updateCronExpression);
    document.getElementById('monthly_time')?.addEventListener('change', updateCronExpression);

    // 监听周几选择变化
    const weekCheckboxes = document.querySelectorAll('#weekly_settings input[type="checkbox"]');
    weekCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateCronExpression);
    });

    // 根据现有的cron表达式初始化界面
    initializeFromExistingCron();

    // 初始化显示
    handleScheduleTypeChange();
}

function initializeFromExistingCron() {
    const cronInput = document.getElementById('cron_expression');
    const cronValue = cronInput?.value?.trim();

    if (!cronValue) {
        // 没有cron表达式，默认选择手动执行
        document.getElementById('schedule_manual').checked = true;
        return;
    }

    // 尝试解析现有的cron表达式并设置对应的界面
    const parts = cronValue.split(' ');
    if (parts.length === 5) {
        const [minute, hour, day, month, dayOfWeek] = parts;

        // 检查是否是每日执行 (day=*, month=*, dayOfWeek=*)
        if (day === '*' && month === '*' && dayOfWeek === '*') {
            document.getElementById('schedule_daily').checked = true;
            document.getElementById('daily_time').value = `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
        }
        // 检查是否是每周执行 (day=*, month=*, dayOfWeek!=*)
        else if (day === '*' && month === '*' && dayOfWeek !== '*') {
            document.getElementById('schedule_weekly').checked = true;
            document.getElementById('weekly_time').value = `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;

            // 设置周几
            const days = dayOfWeek.split(',');
            days.forEach(d => {
                const checkbox = document.getElementById(`week_${d.trim()}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        // 检查是否是每月执行 (day!=*, month=*, dayOfWeek=*)
        else if (day !== '*' && month === '*' && dayOfWeek === '*') {
            document.getElementById('schedule_monthly').checked = true;
            document.getElementById('monthly_time').value = `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
            document.getElementById('monthly_day').value = day;
        }
        else {
            // 复杂的cron表达式，显示高级模式
            document.getElementById('show_advanced_cron').checked = true;
            toggleAdvancedCron();
        }
    }
}

function handleScheduleTypeChange() {
    const selectedType = document.querySelector('input[name="schedule_type"]:checked')?.value;

    // 隐藏所有设置面板
    document.querySelectorAll('.schedule-settings').forEach(panel => {
        panel.style.display = 'none';
    });

    // 显示对应的设置面板
    if (selectedType && selectedType !== 'manual') {
        const panel = document.getElementById(selectedType + '_settings');
        if (panel) {
            panel.style.display = 'block';
        }
    }

    // 更新Cron表达式和预览
    updateCronExpression();
}

function updateCronExpression() {
    const selectedType = document.querySelector('input[name="schedule_type"]:checked')?.value;
    let cronExpression = '';
    let previewText = '';

    switch (selectedType) {
        case 'manual':
            cronExpression = '';
            previewText = '当前设置为手动执行，不会自动运行备份任务';
            break;

        case 'daily':
            const dailyTime = document.getElementById('daily_time')?.value || '02:00';
            const [dailyHour, dailyMinute] = dailyTime.split(':');
            cronExpression = `${dailyMinute} ${dailyHour} * * *`;
            previewText = `每天 ${dailyTime} 自动执行备份任务`;
            break;

        case 'weekly':
            const weeklyTime = document.getElementById('weekly_time')?.value || '02:00';
            const [weeklyHour, weeklyMinute] = weeklyTime.split(':');
            const selectedDays = [];
            const weekCheckboxes = document.querySelectorAll('#weekly_settings input[type="checkbox"]:checked');
            weekCheckboxes.forEach(checkbox => {
                selectedDays.push(checkbox.value);
            });

            if (selectedDays.length > 0) {
                cronExpression = `${weeklyMinute} ${weeklyHour} * * ${selectedDays.join(',')}`;
                const dayNames = selectedDays.map(day => {
                    const names = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
                    return names[parseInt(day)];
                });
                previewText = `每周 ${dayNames.join('、')} ${weeklyTime} 自动执行备份任务`;
            } else {
                cronExpression = '';
                previewText = '请选择至少一个执行日期';
            }
            break;

        case 'monthly':
            const monthlyTime = document.getElementById('monthly_time')?.value || '02:00';
            const [monthlyHour, monthlyMinute] = monthlyTime.split(':');
            const monthlyDay = document.getElementById('monthly_day')?.value || '1';

            if (monthlyDay === '-1') {
                // 月末的特殊处理，这里简化为28日
                cronExpression = `${monthlyMinute} ${monthlyHour} 28 * *`;
                previewText = `每月月末 ${monthlyTime} 自动执行备份任务`;
            } else {
                cronExpression = `${monthlyMinute} ${monthlyHour} ${monthlyDay} * *`;
                previewText = `每月 ${monthlyDay} 日 ${monthlyTime} 自动执行备份任务`;
            }
            break;
    }

    // 更新Cron表达式输入框
    const cronInput = document.getElementById('cron_expression');
    if (cronInput && !document.getElementById('show_advanced_cron')?.checked) {
        cronInput.value = cronExpression;
    }

    // 更新预览文本
    const previewElement = document.getElementById('schedule_preview_text');
    if (previewElement) {
        previewElement.textContent = previewText;

        // 更新预览样式
        const previewAlert = document.querySelector('#schedule_preview .alert');
        if (previewAlert) {
            if (selectedType === 'manual' || (selectedType === 'weekly' && selectedDays && selectedDays.length === 0)) {
                previewAlert.className = 'alert alert-info d-flex align-items-center';
            } else {
                previewAlert.className = 'alert alert-success d-flex align-items-center';
            }
        }
    }
}

function toggleAdvancedCron() {
    const checkbox = document.getElementById('show_advanced_cron');
    const advancedPanel = document.getElementById('advanced_cron_settings');
    const cronInput = document.getElementById('cron_expression');

    if (checkbox.checked) {
        advancedPanel.style.display = 'block';
        if (cronInput) {
            cronInput.removeAttribute('readonly');
            cronInput.addEventListener('input', handleManualCronChange);
        }
    } else {
        advancedPanel.style.display = 'none';
        if (cronInput) {
            cronInput.setAttribute('readonly', 'readonly');
            cronInput.removeEventListener('input', handleManualCronChange);
        }
        // 重新生成Cron表达式
        updateCronExpression();
    }
}

function handleManualCronChange() {
    const cronInput = document.getElementById('cron_expression');
    const previewElement = document.getElementById('schedule_preview_text');

    if (cronInput && previewElement) {
        const cronValue = cronInput.value.trim();
        if (cronValue) {
            previewElement.textContent = `自定义Cron表达式: ${cronValue}`;
            const previewAlert = document.querySelector('#schedule_preview .alert');
            if (previewAlert) {
                previewAlert.className = 'alert alert-warning d-flex align-items-center';
            }
        } else {
            previewElement.textContent = '当前设置为手动执行，不会自动运行备份任务';
            const previewAlert = document.querySelector('#schedule_preview .alert');
            if (previewAlert) {
                previewAlert.className = 'alert alert-info d-flex align-items-center';
            }
        }
    }
}

// 初始化存储配置（用于编辑模式）
function initializeStorageConfigs(taskStorageConfigs, legacyStorageConfigId, legacyRemotePath) {
    // 加载现有的存储配置
    if (taskStorageConfigs && taskStorageConfigs.length > 0) {
        taskStorageConfigs.forEach(config => {
            selectedStorageConfigs.set(config.storage_config_id.toString(), config.remote_path);
        });
    } else if (legacyStorageConfigId && legacyRemotePath) {
        // 向后兼容：加载旧的单存储配置
        selectedStorageConfigs.set(legacyStorageConfigId.toString(), legacyRemotePath);
    }

    // 更新显示
    updateStorageConfigDisplay();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化选项显示状态
    toggleCompression();
    toggleEncryption();

    // 初始化调度设置
    initializeScheduleSettings();
});
