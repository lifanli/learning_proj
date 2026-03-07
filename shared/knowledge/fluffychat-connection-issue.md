# FluffyChat 连接问题诊断

## 问题描述
管理员尝试通过 FluffyChat 连接 `http://192.168.31.56:6167` 失败

## 诊断结果

### 1. 网络连通性
- ✅ `192.168.31.56` 可以 ping 通
- ❌ 端口 `6167` 未监听

### 2. Matrix 服务器实际配置
- **内部地址**: `matrix-local.hiclaw.io:8080` (172.17.0.2:8080)
- **外部地址**: 需要确认

### 3. 问题分析

**可能原因**：
1. Matrix 服务器不在 6167 端口运行（实际在 8080 端口）
2. 6167 可能是 Element Web 或其他服务的端口
3. 防火墙阻止了 6167 端口

## 解决方案

### 方案 A：使用正确的端口
FluffyChat 连接地址改为：
```
http://192.168.31.56:8080
```

### 方案 B：检查 6167 端口服务
```bash
# 检查什么服务在 6167 端口
netstat -tlnp | grep 6167

# 或者检查 docker 容器
docker ps | grep 6167
```

### 方案 C：使用内部地址
如果在同一网络内，可以使用：
```
http://matrix-local.hiclaw.io:8080
```

## FluffyChat 配置步骤

1. 打开 FluffyChat
2. 选择"添加账户"或"切换服务器"
3. 输入服务器地址：`http://192.168.31.56:8080`
4. 输入用户名和密码
5. 登录

## 项目管理小群创建

### 群信息
- **群名**: 项目管理组
- **成员**: 
  - @admin:matrix-local.hiclaw.io:18080
  - @manager:matrix-local.hiclaw.io:18080
  - @project-director:matrix-local.hiclaw.io:18080 (林小雅)
  - @frontend-engineer:matrix-local.hiclaw.io:18080 (陈明轩)
  - @search-worker:matrix-local.hiclaw.io:18080 (苏婉儿)
  - @review-worker:matrix-local.hiclaw.io:18080 (陆思琪)

### 创建命令
```bash
# 使用 matrix-cli 或其他工具创建房间
matrix-cli room create --name "项目管理组" --invite @admin:... --invite @manager:...
```

## 下一步

1. 确认 FluffyChat 使用正确端口连接
2. 创建项目管理小群
3. 邀请所有项目管理人员加入
