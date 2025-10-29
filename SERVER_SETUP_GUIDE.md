# 真实服务器上的API配置指南

## 🎯 您需要在vultr-ats服务器上执行的操作

当前您在**代码仓库环境**，需要切换到**真实服务器**进行配置。

---

## 📝 完整操作步骤

### 1. 登录到您的服务器

```bash
ssh cryptosignal@139.180.157.152
# 或者您正常的SSH登录方式
```

### 2. 拉取最新代码

```bash
cd ~/cryptosignal
git pull origin claude/optimize-coin-analysis-speed-011CUYy6rjvHGXbkToyBt9ja
```

### 3. 配置API密钥

```bash
# 编辑 ~/.bashrc
nano ~/.bashrc

# 在文件末尾添加以下两行：
export BINANCE_API_KEY="Bi4GGFJzm7vZcYf7gUBG2ieXF5ehqMOZhSpaPmXs76vBZDRK6NrP9hksbAP6thjq"
export BINANCE_API_SECRET="dx8ge7JN600f5n8vLd60x8ycPvyeL2SqJ9iKCC6eCIwKLTWUMyaEsnRx2JwcjNQx"

# 保存：Ctrl+O, Enter, Ctrl+X

# 使配置生效
source ~/.bashrc
```

### 4. 验证配置

```bash
# 检查环境变量
echo $BINANCE_API_KEY
# 应该输出：Bi4GGFJzm7vZcYf7gUBG2ieXF5ehqMOZhSpaPmXs76vBZDRK6NrP9hksbAP6thjq

echo $BINANCE_API_SECRET
# 应该输出：dx8ge7JN600f5n8vLd60x8ycPvyeL2SqJ9iKCC6eCIwKLTWUMyaEsnRx2JwcjNQx
```

### 5. 测试API认证

```bash
python3 test_api_auth.py
```

**预期输出**：
```
✅ BINANCE_API_KEY: Bi4GGFJz...thjq (长度: 64)
✅ BINANCE_API_SECRET: ****...jNQx (长度: 64)
✅ 成功获取 X 条清算数据
✅ API认证配置成功！Q因子已启用
```

### 6. 运行完整测试

```bash
python3 test_10d_analysis.py
```

**预期输出** - Q因子应该显示非零值：
```
【BTCUSDT】
  Q(清算密度): +8.5   ✅ 清算数据已获取
  I(独立性): +20.0     ✅ 正常工作

  清算数据: 245条
```

### 7. 验证完整系统

```bash
python3 verify_10d_system.py
```

**预期输出**：
```
🎉 10维因子系统完全正常！
✅ Q因子（清算密度）工作正常
✅ I因子（独立性）工作正常
```

---

## 🔧 故障排查

### 问题1: 仍然显示401错误

**可能原因**：
- API密钥复制错误（有多余空格或字符）
- Binance未启用读取权限

**解决方法**：
```bash
# 检查环境变量长度
echo -n $BINANCE_API_KEY | wc -c
# 应该输出：64

echo -n $BINANCE_API_SECRET | wc -c
# 应该输出：64

# 如果长度不对，说明有多余字符，重新配置
```

### 问题2: IP白名单错误

**症状**：`Invalid IP address`

**解决方法**：
1. 在服务器上检查IP：
   ```bash
   curl ifconfig.me
   ```
2. 确认Binance API设置中的IP白名单包含这个IP
3. 如果不同，更新Binance API设置中的IP白名单

### 问题3: 时间戳错误

**症状**：`Timestamp for this request is outside of the recvWindow`

**解决方法**：
```bash
# 同步服务器时间
sudo ntpdate pool.ntp.org

# 如果没有ntpdate，使用timedatectl
sudo timedatectl set-ntp true
```

---

## 📊 验证清单

配置完成后，确认以下所有项都是✅：

- [ ] 已登录到vultr-ats服务器（139.180.157.152）
- [ ] 已拉取最新代码
- [ ] ~/.bashrc中已添加API密钥
- [ ] source ~/.bashrc已执行
- [ ] echo $BINANCE_API_KEY输出正确
- [ ] python3 test_api_auth.py 成功
- [ ] python3 test_10d_analysis.py 显示Q因子非零
- [ ] python3 verify_10d_system.py 全部通过

---

## 🚀 投入生产使用

当所有测试通过后，启动生产系统：

```bash
# 启动批量扫描器
python3 run_scanner.py

# 或者使用后台运行
nohup python3 run_scanner.py > scanner.log 2>&1 &
```

---

## 📝 一键配置脚本（可选）

如果您想一键完成所有配置，可以运行：

```bash
# 在服务器上执行
cat << 'SCRIPT_EOF' > /tmp/setup_api.sh
#!/bin/bash

echo "配置Binance API..."

# 检查是否已配置
if grep -q "BINANCE_API_KEY" ~/.bashrc; then
    echo "⚠️  API密钥已存在，跳过配置"
else
    echo "" >> ~/.bashrc
    echo "# Binance API 配置（用于Q因子清算数据）" >> ~/.bashrc
    echo 'export BINANCE_API_KEY="Bi4GGFJzm7vZcYf7gUBG2ieXF5ehqMOZhSpaPmXs76vBZDRK6NrP9hksbAP6thjq"' >> ~/.bashrc
    echo 'export BINANCE_API_SECRET="dx8ge7JN600f5n8vLd60x8ycPvyeL2SqJ9iKCC6eCIwKLTWUMyaEsnRx2JwcjNQx"' >> ~/.bashrc
    echo "✅ API密钥已添加到 ~/.bashrc"
fi

# 加载环境变量
source ~/.bashrc

# 验证
echo ""
echo "验证配置："
echo "API Key: ${BINANCE_API_KEY:0:8}...${BINANCE_API_KEY: -4}"
echo "Secret: ****...${BINANCE_API_SECRET: -4}"

echo ""
echo "✅ 配置完成！"
echo ""
echo "下一步："
echo "  source ~/.bashrc"
echo "  python3 test_api_auth.py"

SCRIPT_EOF

# 执行脚本
bash /tmp/setup_api.sh
```

---

## 🔐 安全提醒

1. **权限检查**：确认API只有"读取"权限
2. **IP白名单**：确认设置为 139.180.157.152
3. **定期更换**：建议每3-6个月更换一次API密钥
4. **监控日志**：定期检查Binance API使用日志

---

**配置完成后**，您就可以使用完整的10维因子系统了！

所有配置都已提交到git仓库，您只需要在服务器上设置环境变量即可。
