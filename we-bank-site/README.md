# 演示银行官网模板（部署到阿里云）

> 免责声明：本仓库仅为静态企业官网演示模板，与任何真实银行或机构无关，不提供任何真实金融服务。

## 目录结构

```
/we-bank-site
├─ public/                # 静态页面与资源
│  ├─ index.html
│  ├─ about.html products.html news.html careers.html contact.html
│  └─ assets/
│     ├─ css/styles.css
│     ├─ js/main.js
│     └─ img/logo.svg
├─ nginx/default.conf     # Nginx 静态站点配置
├─ Dockerfile             # 生产镜像
├─ docker-compose.yml     # 本地启动
└─ scripts/
   ├─ deploy-oss.sh       # 部署到 OSS（静态托管/CDN）
   └─ deploy-ecs.sh       # 部署到 ECS（Docker/Nginx）
```

## 本地运行

```bash
cd /workspace/we-bank-site
docker compose up --build -d
# 访问 http://localhost:8080
```

## 方案一：部署到阿里云 OSS（静态托管 + 可选 CDN）

适合纯静态网站，成本低、维护简单。

### 前置条件
- 已创建阿里云账号并开通 OSS
- 安装并配置 aliyun CLI：`aliyun configure`
- 已创建 Bucket（公共读或绑定 CDN）

### 一键部署
```bash
cd /workspace/we-bank-site
export OSS_BUCKET=你的Bucket名
export OSS_REGION=cn-hangzhou   # 按你的地域填写
export OSS_PREFIX=we-bank-site  # 可选：上传到该目录前缀
bash scripts/deploy-oss.sh
```
完成后：
- 直接用 `https://<bucket>.<region>.aliyuncs.com/<prefix>/index.html` 访问，或
- 绑定自定义域名 + CDN 加速 + HTTPS 证书（推荐）

## 方案二：部署到阿里云 ECS（Docker 容器）

适合需要自定义 Nginx、未来扩展到后端服务的场景。

### 前置条件
- 一台可用的 ECS（建议安全组放行 80/443）
- ECS 上已安装 Docker（或使用 Docker 一键安装脚本）
- 可 SSH 访问 ECS

### 一键部署
```bash
cd /workspace/we-bank-site
export ECS_HOST=你的ECS公网IP
export ECS_USER=root               # 如不同请修改
export SSH_KEY=$HOME/.ssh/id_rsa   # 私钥路径
export APP_NAME=we-bank-site-demo  # 可自定义
export REMOTE_PORT=80              # 可改 80/8080 等
bash scripts/deploy-ecs.sh
```
完成后访问：`http://<ECS_HOST>:<REMOTE_PORT>`

### HTTPS（可选）
- 在 ECS 上使用 Nginx 反向代理 + 证书（如 `certbot`/阿里云证书服务），将 443 代理到容器 80
- 或使用 SLB/ALB + 证书，监听 443 并转发到容器 80

## 自定义与注意事项
- 本模板所有文案仅为示例，部署到公网前请替换品牌、文案与法律合规页。
- 如果使用 OSS 静态托管，注意合理设置缓存策略与 CDN 回源配置。
- 如需多环境（dev/stage/prod），可分不同 Bucket/路径或不同 ECS。

## 版权与许可
- 本模板仅用于演示与学习，不得用于冒用真实机构、误导用户或从事任何违法违规行为。