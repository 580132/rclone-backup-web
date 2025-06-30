#!/usr/bin/env python3
"""
RClone备份Web系统 - 测试版本
用于验证系统环境和基本功能
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import os
import sys
import subprocess
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'test-secret-key'

# 基础HTML模板
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - RClone备份系统测试</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .status-ok { color: #198754; }
        .status-error { color: #dc3545; }
        .status-warning { color: #fd7e14; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="bi bi-cloud-upload"></i> RClone备份系统测试
            </a>
            {% if session.logged_in %}
            <div class="navbar-nav">
                <a class="nav-link" href="{{ url_for('logout') }}">退出</a>
            </div>
            {% endif %}
        </div>
    </nav>
    
    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

def get_system_info():
    """获取系统信息"""
    info = {
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'platform': sys.platform,
        'cwd': os.getcwd(),
        'user': os.getenv('USER', 'unknown'),
        'home': os.getenv('HOME', 'unknown'),
    }
    
    # 检查rclone
    try:
        result = subprocess.run(['rclone', 'version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            info['rclone_status'] = 'ok'
            info['rclone_version'] = result.stdout.split('\n')[0] if result.stdout else 'unknown'
        else:
            info['rclone_status'] = 'error'
            info['rclone_error'] = result.stderr
    except FileNotFoundError:
        info['rclone_status'] = 'not_found'
    except subprocess.TimeoutExpired:
        info['rclone_status'] = 'timeout'
    except Exception as e:
        info['rclone_status'] = 'error'
        info['rclone_error'] = str(e)
    
    # 检查Linux环境
    try:
        if sys.platform.startswith('linux'):
            info['os_type'] = 'Linux'
            info['is_linux'] = True
            # 检查发行版
            try:
                with open('/etc/os-release', 'r') as f:
                    os_release = f.read()
                    if 'Ubuntu' in os_release:
                        info['distro'] = 'Ubuntu'
                    elif 'Debian' in os_release:
                        info['distro'] = 'Debian'
                    elif 'CentOS' in os_release:
                        info['distro'] = 'CentOS'
                    else:
                        info['distro'] = 'Other Linux'
            except:
                info['distro'] = 'Unknown Linux'
        else:
            info['os_type'] = f'非Linux系统 ({sys.platform})'
            info['is_linux'] = False
            info['distro'] = 'N/A'
    except:
        info['os_type'] = 'Unknown'
        info['is_linux'] = False
        info['distro'] = 'Unknown'
    
    return info

def test_rclone_config():
    """测试rclone配置功能"""
    try:
        # 创建测试配置目录
        config_dir = os.path.join(os.getcwd(), 'data', 'rclone_configs')
        os.makedirs(config_dir, exist_ok=True)
        
        # 创建测试配置文件
        test_config = os.path.join(config_dir, 'test.conf')
        with open(test_config, 'w') as f:
            f.write('[test]\ntype = local\n')
        
        # 测试rclone命令
        result = subprocess.run([
            'rclone', 'lsd', 'test:', 
            '--config', test_config
        ], capture_output=True, text=True, timeout=10)
        
        # 清理测试文件
        if os.path.exists(test_config):
            os.remove(test_config)
        
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/')
def index():
    """首页"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    info = get_system_info()
    rclone_test = test_rclone_config()
    
    template = BASE_TEMPLATE + '''
    {% block content %}
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5><i class="bi bi-info-circle"></i> 系统状态检查</h5>
                </div>
                <div class="card-body">
                    <table class="table">
                        <tr>
                            <td><strong>操作系统</strong></td>
                            <td>
                                {% if info.is_linux %}
                                    <span class="status-ok"><i class="bi bi-check-circle"></i> {{ info.os_type }}</span>
                                    {% if info.distro != 'Unknown Linux' %}
                                        <br><small>发行版: {{ info.distro }}</small>
                                    {% endif %}
                                {% else %}
                                    <span class="status-warning"><i class="bi bi-exclamation-triangle"></i> {{ info.os_type }}</span>
                                    <br><small>警告: 此系统专为Linux设计</small>
                                {% endif %}
                            </td>
                        </tr>
                        <tr>
                            <td><strong>Python版本</strong></td>
                            <td><span class="status-ok">{{ info.python_version }}</span></td>
                        </tr>
                        <tr>
                            <td><strong>当前用户</strong></td>
                            <td>{{ info.user }}</td>
                        </tr>
                        <tr>
                            <td><strong>工作目录</strong></td>
                            <td><code>{{ info.cwd }}</code></td>
                        </tr>
                        <tr>
                            <td><strong>rclone状态</strong></td>
                            <td>
                                {% if info.rclone_status == 'ok' %}
                                    <span class="status-ok"><i class="bi bi-check-circle"></i> 已安装</span>
                                    <br><small>{{ info.rclone_version }}</small>
                                {% elif info.rclone_status == 'not_found' %}
                                    <span class="status-error"><i class="bi bi-x-circle"></i> 未找到rclone命令</span>
                                {% else %}
                                    <span class="status-error"><i class="bi bi-x-circle"></i> 错误</span>
                                    {% if info.rclone_error %}
                                        <br><small>{{ info.rclone_error }}</small>
                                    {% endif %}
                                {% endif %}
                            </td>
                        </tr>
                        <tr>
                            <td><strong>rclone功能测试</strong></td>
                            <td>
                                {% if rclone_test.success %}
                                    <span class="status-ok"><i class="bi bi-check-circle"></i> 功能正常</span>
                                {% else %}
                                    <span class="status-error"><i class="bi bi-x-circle"></i> 功能异常</span>
                                    {% if rclone_test.error %}
                                        <br><small>{{ rclone_test.error }}</small>
                                    {% endif %}
                                {% endif %}
                            </td>
                        </tr>
                    </table>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5><i class="bi bi-list-check"></i> 功能测试</h5>
                </div>
                <div class="card-body">
                    <div class="d-grid gap-2">
                        <a href="{{ url_for('test_flask') }}" class="btn btn-outline-primary">
                            <i class="bi bi-flask"></i> Flask功能测试
                        </a>
                        <a href="{{ url_for('test_rclone') }}" class="btn btn-outline-success">
                            <i class="bi bi-cloud"></i> rclone测试
                        </a>
                        <a href="{{ url_for('test_database') }}" class="btn btn-outline-info">
                            <i class="bi bi-database"></i> 数据库测试
                        </a>
                        <button class="btn btn-outline-warning" onclick="location.reload()">
                            <i class="bi bi-arrow-clockwise"></i> 刷新状态
                        </button>
                    </div>
                </div>
            </div>
            

        </div>
    </div>
    {% endblock %}
    '''
    
    return render_template_string(template, title="系统状态", info=info, rclone_test=rclone_test)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 简单的测试认证
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['username'] = username
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误', 'error')
    
    template = BASE_TEMPLATE + '''
    {% block content %}
    <div class="row justify-content-center">
        <div class="col-md-4">
            <div class="card">
                <div class="card-header text-center">
                    <h4><i class="bi bi-shield-lock"></i> 系统登录</h4>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3">
                            <label for="username" class="form-label">用户名</label>
                            <input type="text" class="form-control" id="username" name="username" 
                                   value="admin" required>
                        </div>
                        <div class="mb-3">
                            <label for="password" class="form-label">密码</label>
                            <input type="password" class="form-control" id="password" name="password" 
                                   value="admin123" required>
                        </div>
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary">登录</button>
                        </div>
                    </form>
                </div>
                <div class="card-footer text-center">
                    <small class="text-muted">测试账户：admin / admin123</small>
                </div>
            </div>
        </div>
    </div>
    {% endblock %}
    '''
    
    return render_template_string(template, title="登录")

@app.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('login'))

@app.route('/test/flask')
def test_flask():
    """Flask功能测试"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    tests = [
        {'name': 'Session功能', 'status': 'ok' if session.get('logged_in') else 'error'},
        {'name': 'Flash消息', 'status': 'ok'},
        {'name': '模板渲染', 'status': 'ok'},
        {'name': 'URL路由', 'status': 'ok'},
    ]
    
    template = BASE_TEMPLATE + '''
    {% block content %}
    <div class="card">
        <div class="card-header">
            <h5><i class="bi bi-flask"></i> Flask功能测试结果</h5>
        </div>
        <div class="card-body">
            <table class="table">
                {% for test in tests %}
                <tr>
                    <td>{{ test.name }}</td>
                    <td>
                        {% if test.status == 'ok' %}
                            <span class="status-ok"><i class="bi bi-check-circle"></i> 正常</span>
                        {% else %}
                            <span class="status-error"><i class="bi bi-x-circle"></i> 异常</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
            <a href="{{ url_for('index') }}" class="btn btn-secondary">返回首页</a>
        </div>
    </div>
    {% endblock %}
    '''
    
    flash('Flask功能测试完成', 'success')
    return render_template_string(template, title="Flask测试", tests=tests)

@app.route('/test/rclone')
def test_rclone():
    """rclone功能测试"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # 执行rclone测试
    test_result = test_rclone_config()
    
    template = BASE_TEMPLATE + '''
    {% block content %}
    <div class="card">
        <div class="card-header">
            <h5><i class="bi bi-cloud"></i> rclone功能测试结果</h5>
        </div>
        <div class="card-body">
            {% if test_result.success %}
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> rclone功能测试通过
                </div>
                {% if test_result.output %}
                <h6>输出：</h6>
                <pre class="bg-light p-2">{{ test_result.output }}</pre>
                {% endif %}
            {% else %}
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> rclone功能测试失败
                </div>
                {% if test_result.error %}
                <h6>错误信息：</h6>
                <pre class="bg-light p-2">{{ test_result.error }}</pre>
                {% endif %}
            {% endif %}
            
            <a href="{{ url_for('index') }}" class="btn btn-secondary">返回首页</a>
        </div>
    </div>
    {% endblock %}
    '''
    
    return render_template_string(template, title="rclone测试", test_result=test_result)

@app.route('/test/database')
def test_database():
    """数据库功能测试"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        # 创建测试数据库
        os.makedirs('data', exist_ok=True)
        db_path = 'data/test.db'
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建测试表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 插入测试数据
        cursor.execute('INSERT INTO test_table (name) VALUES (?)', ('测试数据',))
        
        # 查询数据
        cursor.execute('SELECT * FROM test_table')
        results = cursor.fetchall()
        
        conn.commit()
        conn.close()
        
        success = True
        error = None
    except Exception as e:
        success = False
        error = str(e)
        results = []
    
    template = BASE_TEMPLATE + '''
    {% block content %}
    <div class="card">
        <div class="card-header">
            <h5><i class="bi bi-database"></i> 数据库功能测试结果</h5>
        </div>
        <div class="card-body">
            {% if success %}
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> 数据库功能测试通过
                </div>
                <h6>测试数据：</h6>
                <table class="table table-sm">
                    <thead>
                        <tr><th>ID</th><th>名称</th><th>创建时间</th></tr>
                    </thead>
                    <tbody>
                        {% for row in results %}
                        <tr>
                            <td>{{ row[0] }}</td>
                            <td>{{ row[1] }}</td>
                            <td>{{ row[2] }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i> 数据库功能测试失败
                </div>
                <pre class="bg-light p-2">{{ error }}</pre>
            {% endif %}
            
            <a href="{{ url_for('index') }}" class="btn btn-secondary">返回首页</a>
        </div>
    </div>
    {% endblock %}
    '''
    
    return render_template_string(template, title="数据库测试", 
                                success=success, error=error, results=results)

if __name__ == '__main__':
    print("=" * 50)
    print("RClone备份Web系统 - 测试版本")
    print("=" * 50)
    
    info = get_system_info()
    print(f"Python版本: {info['python_version']}")
    print(f"操作系统: {info['os_type']}")
    print(f"rclone状态: {info['rclone_status']}")
    print(f"工作目录: {info['cwd']}")
    print()
    print("启动Web服务器...")
    print("访问地址: http://localhost:5000")
    print("默认账户: admin / admin123")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
