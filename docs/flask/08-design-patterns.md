# Flask设计模式应用深度解析

## 1. 设计模式概述

### 1.1 设计目标
- 提高代码可维护性
- 降低系统复杂度
- 提供可重用的解决方案
- 遵循面向对象设计原则

## 2. 创建型模式

### 2.1 工厂模式
```python
class ViewFactory:
    @staticmethod
    def create_view(view_type):
        """
        根据类型动态创建视图
        
        参数:
        - view_type: 视图类型
        
        返回: 对应的视图处理器
        """
        views = {
            'user': UserView,
            'admin': AdminView,
            'public': PublicView
        }
        return views.get(view_type, DefaultView)
```

### 2.2 单例模式
```python
class Singleton:
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

class DatabaseConnection(Singleton):
    def __init__(self):
        if not hasattr(self, 'connection'):
            self.connection = create_db_connection()
```

## 3. 结构型模式

### 3.1 装饰器模式
```python
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')
```

### 3.2 适配器模式
```python
class LegacyUserService:
    def get_user(self, user_id):
        # 老系统用户查询
        pass

class UserServiceAdapter:
    def __init__(self, legacy_service):
        self._legacy_service = legacy_service
    
    def fetch_user(self, user_id):
        # 适配新系统接口
        return self._legacy_service.get_user(user_id)
```

## 4. 行为型模式

### 4.1 观察者模式
```python
class EventDispatcher:
    def __init__(self):
        self._listeners = {}
    
    def register(self, event_type, listener):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)
    
    def dispatch(self, event_type, event_data):
        for listener in self._listeners.get(event_type, []):
            listener(event_data)

# 使用示例
dispatcher = EventDispatcher()
dispatcher.register('user_registered', send_welcome_email)
dispatcher.register('user_registered', log_registration)
```

### 4.2 策略模式
```python
class AuthStrategy:
    def authenticate(self, credentials):
        raise NotImplementedError

class DatabaseAuthStrategy(AuthStrategy):
    def authenticate(self, credentials):
        # 数据库认证
        pass

class LDAPAuthStrategy(AuthStrategy):
    def authenticate(self, credentials):
        # LDAP认证
        pass

class AuthenticationService:
    def __init__(self, strategy):
        self._strategy = strategy
    
    def login(self, credentials):
        return self._strategy.authenticate(credentials)
```

## 5. 架构型模式

### 5.1 依赖注入
```python
class UserService:
    def __init__(self, user_repository):
        self._repository = user_repository
    
    def get_user(self, user_id):
        return self._repository.find_by_id(user_id)

# 依赖注入
user_repo = SQLAlchemyUserRepository()
user_service = UserService(user_repo)
```

### 5.2 仓储模式
```python
class Repository:
    def __init__(self, db):
        self._db = db
    
    def find_by_id(self, id):
        return self._db.session.query(self.model).get(id)
    
    def save(self, entity):
        self._db.session.add(entity)
        self._db.session.commit()
```

## 6. 并发模式

### 6.1 线程安全单例
```python
import threading

class ThreadSafeSingleton:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

## 7. 性能模式

### 7.1 享元模式
```python
class ViewCache:
    _view_cache = {}
    
    @classmethod
    def get_view(cls, view_name):
        if view_name not in cls._view_cache:
            cls._view_cache[view_name] = importlib.import_module(view_name)
        return cls._view_cache[view_name]
```

## 8. 安全设计模式

### 8.1 命令模式（安全操作）
```python
class SecurityCommand:
    def execute(self, user, action):
        if self.can_execute(user, action):
            action.perform()
        else:
            raise PermissionDenied()
    
    def can_execute(self, user, action):
        # 权限检查逻辑
        pass
```

## 9. 最佳实践

### 9.1 设计模式应用原则
- 不过度设计
- 根据实际需求选择模式
- 保持代码简洁
- 优先考虑可读性

### 9.2 常见反模式
- 过度使用复杂模式
- 为使用模式而使用模式
- 忽视具体业务场景

## 结语

Flask通过灵活的设计模式应用，为开发者提供了优雅、可扩展的Web开发解决方案，体现了Python"简单而强大"的设计哲学。