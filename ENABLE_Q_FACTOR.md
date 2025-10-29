# 启用Q因子（清算密度）- API认证配置

## 问题说明

Q因子需要从Binance获取清算数据，但Binance的清算数据端点需要API认证。

## 解决方案

设置Binance API Key和Secret环境变量，系统将自动使用签名API获取清算数据。

## 配置步骤

### 1. 获取Binance API Key

访问Binance官网获取API Key和Secret：
- 登录 Binance 账户
- 访问 API管理页面
- 创建新API Key（**只需读取权限，不需要交易权限**）
- 记录API Key和API Secret

### 2. 设置环境变量

有两种方式设置：

#### 方式1：命令行临时设置（推荐测试用）

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"

# 运行测试
PYTHONPATH=/home/user/cryptosignal python3 test_10d_analysis.py
```

#### 方式2：永久设置（推荐生产环境）

编辑 `~/.bashrc` 或 `~/.profile`：

```bash
nano ~/.bashrc
```

添加以下行：

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

保存并生效：

```bash
source ~/.bashrc
```

### 3. 验证配置

```bash
# 检查环境变量是否设置
echo $BINANCE_API_KEY
echo $BINANCE_API_SECRET

# 运行测试
PYTHONPATH=/home/user/cryptosignal python3 test_10d_analysis.py
```

## 预期结果

配置成功后，Q因子应显示非零值：

```
【BTCUSDT】
  Q(清算密度): +8.5     # ✅ 非零值
  I(独立性): +20.0       # ✅ 已正常工作

  清算数据: 245条        # ✅ 成功获取
```

## 安全提示

⚠️ **重要安全提示**：

1. **API权限**：只需启用"读取"权限，不要启用"交易"或"提现"权限
2. **IP白名单**：建议在Binance设置IP白名单，限制API只能从服务器IP访问
3. **定期更换**：定期更换API Key和Secret
4. **不要泄露**：不要将API Key和Secret提交到git或公开分享

## 降级处理

如果不配置API认证，Q因子将返回0，但其他9个因子仍正常工作：

- ✅ T(趋势), M(动量), S(结构), V(成交量)
- ✅ C(CVD), O(持仓量)
- ✅ L(流动性), B(基差+资金费)
- ❌ Q(清算密度) - 需要API认证
- ✅ I(独立性)

## 技术细节

系统会自动尝试两种API端点：

1. **公开接口** `/fapi/v1/forceOrders` - 无需签名（优先尝试）
2. **认证接口** `/fapi/v1/allForceOrders` - 需要签名（公开接口失败时自动降级）

代码实现：`ats_core/sources/binance.py` 中的 `get_liquidations()` 函数

## 故障排查

### 问题1: 仍然提示"Unauthorized"

```bash
# 检查环境变量是否正确设置
env | grep BINANCE

# 确保没有多余的引号或空格
```

### 问题2: "Invalid API-key, IP, or permissions"

- 检查API Key是否正确
- 检查是否启用了"读取"权限
- 检查IP白名单设置（如果启用了）

### 问题3: "Timestamp for this request is outside of the recvWindow"

- 检查服务器时间是否同步
```bash
# 检查时间
date
# 同步时间
sudo ntpdate pool.ntp.org
```

## 帮助和支持

如有问题，请检查：
1. Binance API文档: https://binance-docs.github.io/apidocs/futures/en/
2. 系统日志中的详细错误信息
3. 确认API Key权限设置正确
