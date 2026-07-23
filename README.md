# Notice List API

一个简单的公开通知列表只读 JSON API。服务按请求读取指定页面，并使用短时内存缓存降低对上游网站的访问频率。

本项目没有机器人、后台轮询、邮件、消息推送或用户状态功能。它只访问公开网页，不需要教务系统账号，也不绕过登录、验证码或访问控制。

## API

### 健康检查

```http
GET /health
```

```json
{"status":"ok","service":"notice-api"}
```

### 当前通知列表

```http
GET /api/v1/notices
```

响应中的 `data` 按来源页面顺序排列；`meta.stale` 表示上游暂时不可用时是否返回了过期缓存。

```json
{
  "data": [
    {
      "title": "通知标题",
      "published_date": "2026-07-23",
      "url": "https://jwc.cugb.edu.cn/c/example.shtml"
    }
  ],
  "meta": {
    "source": "https://jwc.cugb.edu.cn/xszq/",
    "fetched_at": "2026-07-23T06:00:00+00:00",
    "stale": false,
    "count": 1
  }
}
```

### 最新一条通知

```http
GET /api/v1/notices/latest
```

## 运行

要求 Python 3.10 或更高版本，运行时没有第三方依赖。

```powershell
Copy-Item config.example.json config.json
python -m cugb_jwc_api --config config.json check-config
python -m cugb_jwc_api --config config.json serve
```

默认监听 `http://127.0.0.1:8000`。也可以覆盖地址和端口：

```powershell
python -m cugb_jwc_api --config config.json serve --host 0.0.0.0 --port 8080
```

调用示例：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/notices
```

## 配置

```json
{
  "source_url": "https://jwc.cugb.edu.cn/xszq/",
  "request_timeout_seconds": 10,
  "request_retries": 2,
  "cache_ttl_seconds": 60,
  "server": {
    "host": "127.0.0.1",
    "port": 8000
  }
}
```

缓存只保存在进程内存中，不会记录用户请求或在后台主动访问上游。缓存到期后的第一个 API 请求会刷新数据；若刷新失败但已有旧缓存，响应会返回旧数据并将 `meta.stale` 设为 `true`。首次读取失败则返回 HTTP 502。

若要对公网提供服务，建议在前面部署带 HTTPS、访问日志和限流的反向代理。默认只监听本机地址。

## 测试

```powershell
python -m unittest discover -s tests -v
```

自动化测试使用合成 HTML 和模拟数据源，不访问网络。

## 合规

请合理设置缓存时间，避免对上游网站造成不必要的请求。网站结构变化可能导致解析失败；API 会返回明确错误，而不会把空页面伪装成正常结果。

## 许可证

本项目采用 [MIT License](LICENSE)。该许可证仅覆盖本仓库中的原创实现，不代表来源网站的内容或标识采用相同许可证。
