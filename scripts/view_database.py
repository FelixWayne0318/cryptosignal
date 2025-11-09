#!/usr/bin/env python3
# coding: utf-8
"""
数据库查看工具 - 生成HTML报告和JSON数据

用法：
    # 生成HTML报告（可在手机浏览器查看）
    python scripts/view_database.py --html
    
    # 生成JSON数据
    python scripts/view_database.py --json
    
    # 查看最近N条信号
    python scripts/view_database.py --recent 20
    
    # 查看特定币种
    python scripts/view_database.py --symbol BTCUSDT
"""

import os
import sys
import json
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# UTC+8时区
TZ_UTC8 = timezone(timedelta(hours=8))

class DatabaseViewer:
    """数据库查看器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.expanduser("~/cryptosignal/data/analysis.db")
        
        self.db_path = db_path
        
        if not os.path.exists(db_path):
            print(f"❌ 数据库文件不存在: {db_path}")
            sys.exit(1)
    
    def get_signal_count(self) -> int:
        """获取信号总数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM signal_analysis;")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_recent_signals(self, limit: int = 10) -> List[Dict]:
        """获取最近的信号"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                signal_id,
                timestamp,
                symbol,
                side,
                confidence,
                calibrated_probability,
                calibrated_ev,
                all_gates_passed,
                full_data
            FROM signal_analysis
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in rows:
            signal = dict(row)
            # 转换时间戳
            signal['time_str'] = datetime.fromtimestamp(
                signal['timestamp'] / 1000, 
                tz=TZ_UTC8
            ).strftime('%Y-%m-%d %H:%M:%S')
            
            # 解析full_data获取v7.2字段
            if signal['full_data']:
                try:
                    full_data = json.loads(signal['full_data'])
                    v72 = full_data.get('v72_enhancements', {})
                    signal['F_v2'] = v72.get('F_v2', 0)
                    signal['I_v2'] = v72.get('I_v2', 0)
                    signal['gates_detail'] = v72.get('gates', {})
                except:
                    pass
            
            signals.append(signal)
        
        return signals
    
    def get_scan_statistics(self, days: int = 7) -> List[Dict]:
        """获取扫描统计"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        start_time = datetime.now(TZ_UTC8) - timedelta(days=days)
        start_ts = int(start_time.timestamp() * 1000)
        
        cursor.execute("""
            SELECT *
            FROM scan_statistics
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """, (start_ts,))
        
        rows = cursor.fetchall()
        conn.close()
        
        scans = []
        for row in rows:
            scan = dict(row)
            scan['time_str'] = datetime.fromtimestamp(
                scan['timestamp'] / 1000,
                tz=TZ_UTC8
            ).strftime('%Y-%m-%d %H:%M:%S')
            scans.append(scan)
        
        return scans
    
    def generate_html_report(self, output_path: str = None):
        """生成HTML报告（手机可查看）"""
        if output_path is None:
            output_path = project_root / "reports" / "database_report.html"
        
        signals = self.get_recent_signals(50)
        scans = self.get_scan_statistics(7)
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据库信号报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 10px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1, h2 {{
            color: #333;
        }}
        .summary {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat {{
            display: inline-block;
            margin-right: 20px;
            font-size: 14px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2196F3;
        }}
        table {{
            width: 100%;
            background: white;
            border-collapse: collapse;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #2196F3;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-success {{
            background: #4CAF50;
            color: white;
        }}
        .badge-danger {{
            background: #f44336;
            color: white;
        }}
        .badge-long {{
            background: #2196F3;
            color: white;
        }}
        .badge-short {{
            background: #FF9800;
            color: white;
        }}
        @media (max-width: 768px) {{
            table {{
                font-size: 12px;
            }}
            th, td {{
                padding: 8px 4px;
            }}
            .stat {{
                display: block;
                margin-bottom: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 交易信号数据库报告</h1>
        
        <div class="summary">
            <div class="stat">
                <div>总信号数</div>
                <div class="stat-value">{len(signals)}</div>
            </div>
            <div class="stat">
                <div>扫描次数</div>
                <div class="stat-value">{len(scans)}</div>
            </div>
            <div class="stat">
                <div>更新时间</div>
                <div style="font-size:14px">{datetime.now(TZ_UTC8).strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
        </div>
        
        <h2>🎯 最近信号 (前50条)</h2>
        <table>
            <thead>
                <tr>
                    <th>时间</th>
                    <th>币种</th>
                    <th>方向</th>
                    <th>置信度</th>
                    <th>概率</th>
                    <th>EV</th>
                    <th>F因子</th>
                    <th>I因子</th>
                    <th>闸门</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for sig in signals:
            gates_badge = "✅" if sig['all_gates_passed'] else "❌"
            side_badge = f'<span class="badge badge-long">{sig["side"]}</span>' if sig['side'] == 'LONG' else f'<span class="badge badge-short">{sig["side"]}</span>'
            
            html += f"""
                <tr>
                    <td>{sig['time_str']}</td>
                    <td><strong>{sig['symbol']}</strong></td>
                    <td>{side_badge}</td>
                    <td>{sig['confidence']:.1f}</td>
                    <td>{sig['calibrated_probability']:.3f}</td>
                    <td>{sig['calibrated_ev']:+.3f}</td>
                    <td>{sig.get('F_v2', 0):.0f}</td>
                    <td>{sig.get('I_v2', 0):.0f}</td>
                    <td>{gates_badge}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
        
        <h2>📈 扫描统计 (最近7天)</h2>
        <table>
            <thead>
                <tr>
                    <th>时间</th>
                    <th>扫描币种</th>
                    <th>发现信号</th>
                    <th>平均Conf</th>
                    <th>耗时</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for scan in scans:
            html += f"""
                <tr>
                    <td>{scan['time_str']}</td>
                    <td>{scan['total_symbols']}</td>
                    <td>{scan['signals_found']}</td>
                    <td>{scan['avg_confidence']:.1f}</td>
                    <td>{scan['scan_duration_sec']:.1f}s</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
        
        <p style="text-align:center; color:#999; margin-top:30px;">
            生成时间: """ + datetime.now(TZ_UTC8).strftime('%Y-%m-%d %H:%M:%S') + """<br>
            CryptoSignal v7.2 数据库查看器
        </p>
    </div>
</body>
</html>
"""
        
        # 写入文件
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ HTML报告已生成: {output_path}")
        print(f"📱 手机查看方式：")
        print(f"   1. 在GitHub仓库中访问: reports/database_report.html")
        print(f"   2. 或在服务器上运行: python3 -m http.server 8000")
        print(f"      然后访问: http://服务器IP:8000/reports/database_report.html")
        
        return str(output_path)
    
    def export_json(self, output_path: str = None):
        """导出JSON数据"""
        if output_path is None:
            output_path = project_root / "reports" / "database_export.json"
        
        signals = self.get_recent_signals(100)
        scans = self.get_scan_statistics(7)
        
        data = {
            'export_time': datetime.now(TZ_UTC8).isoformat(),
            'total_signals': len(signals),
            'signals': signals,
            'scans': scans
        }
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON数据已导出: {output_path}")
        return str(output_path)
    
    def print_summary(self):
        """打印摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("=" * 70)
        print("📊 数据库摘要")
        print("=" * 70)
        
        # 信号统计
        cursor.execute("SELECT COUNT(*) FROM signal_analysis;")
        total_signals = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM signal_analysis WHERE all_gates_passed = 1;")
        passed_signals = cursor.fetchone()[0]
        
        print(f"\n✅ 信号统计:")
        print(f"   总信号数: {total_signals}")
        print(f"   通过闸门: {passed_signals} ({passed_signals/total_signals*100:.1f}%)" if total_signals > 0 else "   通过闸门: 0")
        
        # 扫描统计
        cursor.execute("SELECT COUNT(*) FROM scan_statistics;")
        total_scans = cursor.fetchone()[0]
        
        print(f"\n📈 扫描统计:")
        print(f"   总扫描次数: {total_scans}")
        
        # 最近信号
        if total_signals > 0:
            cursor.execute("""
                SELECT symbol, side, confidence, all_gates_passed, timestamp
                FROM signal_analysis
                ORDER BY timestamp DESC
                LIMIT 5
            """)
            
            print(f"\n🎯 最近5个信号:")
            for row in cursor.fetchall():
                symbol, side, conf, gates, ts = row
                time_str = datetime.fromtimestamp(ts/1000, tz=TZ_UTC8).strftime('%m-%d %H:%M')
                gates_str = "✅" if gates else "❌"
                print(f"   {time_str} | {symbol:10s} | {side:5s} | Conf={conf:5.1f} | {gates_str}")
        
        conn.close()
        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description='数据库查看工具')
    parser.add_argument('--html', action='store_true', help='生成HTML报告')
    parser.add_argument('--json', action='store_true', help='导出JSON数据')
    parser.add_argument('--recent', type=int, metavar='N', help='显示最近N条信号')
    parser.add_argument('--symbol', type=str, help='查看特定币种')
    parser.add_argument('--db', type=str, help='数据库路径（默认: ~/cryptosignal/data/analysis.db）')
    
    args = parser.parse_args()
    
    viewer = DatabaseViewer(args.db)
    
    if args.html:
        viewer.generate_html_report()
    elif args.json:
        viewer.export_json()
    elif args.recent:
        signals = viewer.get_recent_signals(args.recent)
        print(f"\n📊 最近{args.recent}条信号:\n")
        for sig in signals:
            print(f"{sig['time_str']} | {sig['symbol']:10s} | {sig['side']:5s} | "
                  f"Conf={sig['confidence']:5.1f} | P={sig['calibrated_probability']:.3f} | "
                  f"Gates={'✅' if sig['all_gates_passed'] else '❌'}")
    else:
        viewer.print_summary()


if __name__ == '__main__':
    main()
