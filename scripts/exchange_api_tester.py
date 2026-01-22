#!/usr/bin/env python3
"""
交易所API測試 - 極簡穩定版
"""

import asyncio
import aiohttp
import time
import statistics
from datetime import datetime

async def test_exchange(session, name, url, timeout=10):
    """測試單個交易所"""
    start_time = time.time()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            response_time = (time.time() - start_time) * 1000  # 轉為毫秒
            
            if response.status == 200:
                try:
                    data = await response.json()
                    # 基本驗證
                    if (isinstance(data, dict) and len(data) > 0) or \
                       (isinstance(data, list) and len(data) > 0):
                        return {
                            "name": name,
                            "success": True,
                            "response_time": response_time,
                            "error": None,
                            "data_size": len(str(data))
                        }
                    else:
                        return {
                            "name": name,
                            "success": False,
                            "response_time": response_time,
                            "error": "數據格式無效",
                            "data_size": 0
                        }
                except:
                    # 如果能收到200，即使解析失敗也認為連接成功
                    return {
                        "name": name,
                        "success": True,
                        "response_time": response_time,
                        "error": "JSON解析失敗但連接成功",
                        "data_size": 0
                    }
            else:
                return {
                    "name": name,
                    "success": False,
                    "response_time": response_time,
                    "error": f"HTTP {response.status}",
                    "data_size": 0
                }
    except asyncio.TimeoutError:
        return {
            "name": name,
            "success": False,
            "response_time": (time.time() - start_time) * 1000,
            "error": "Timeout",
            "data_size": 0
        }
    except Exception as e:
        return {
            "name": name,
            "success": False,
            "response_time": (time.time() - start_time) * 1000,
            "error": str(e)[:50],
            "data_size": 0
        }

async def main():
    """主測試函數"""
    print("=" * 65)
    print("交易所API穩定性測試")
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    
    # 交易所API列表（優化版）
    exchanges = [
        ("Binance", "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"),
        ("KuCoin", "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT"),
        ("Gate.io", "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT"),
        ("MEXC", "https://api.mexc.com/api/v3/ticker/24hr?symbol=BTCUSDT"),
        ("Huobi", "https://api.huobi.pro/market/detail/merged?symbol=btcusdt"),
        ("Bitget", "https://api.bitget.com/api/spot/v1/market/ticker?symbol=BTCUSDT"),
        ("OKX", "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"),
        ("Pionex", "https://api.pionex.com/api/v1/market/ticker?symbol=BTC_USDT"),
    ]
    
    print(f"\n測試 {len(exchanges)} 個交易所...\n")
    
    async with aiohttp.ClientSession() as session:
        # 並發測試所有交易所
        tasks = [test_exchange(session, name, url) for name, url in exchanges]
        results = await asyncio.gather(*tasks)
    
    # 統計結果
    success_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]
    
    response_times = [r["response_time"] for r in success_results]
    
    # 顯示詳細結果
    print("詳細結果:")
    print("-" * 65)
    
    for result in results:
        if result["success"]:
            print(f"✅ {result['name']:10} | 成功 | 時間: {result['response_time']:5.0f}ms")
        else:
            print(f"❌ {result['name']:10} | 失敗 | 時間: {result['response_time']:5.0f}ms | {result['error']}")
    
    print("-" * 65)
    
    # 顯示統計
    success_rate = (len(success_results) / len(results)) * 100
    
    if response_times:
        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"📊 成功率: {len(success_results)}/{len(results)} ({success_rate:.1f}%)")
        print(f"⏱️  平均響應: {avg_time:.0f}ms (最快: {min_time:.0f}ms, 最慢: {max_time:.0f}ms)")
    else:
        print(f"📊 成功率: {len(success_results)}/{len(results)} ({success_rate:.1f}%)")
        print("⏱️  平均響應: N/A")
    
    # 生成報告文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"exchange_api_test_report_{timestamp}.txt"
    
    report_lines = []
    report_lines.append("=" * 65)
    report_lines.append("交易所API測試報告")
    report_lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 65)
    
    for result in results:
        status = "✅ 成功" if result["success"] else "❌ 失敗"
        report_lines.append(f"{result['name']:10} | {status} | 時間: {result['response_time']:5.0f}ms")
        if result["error"]:
            report_lines.append(f"     錯誤: {result['error']}")
    
    report_lines.append("-" * 65)
    report_lines.append(f"總成功率: {success_rate:.1f}%")
    
    if response_times:
        report_lines.append(f"平均響應: {statistics.mean(response_times):.0f}ms")
    
    # 推薦最佳交易所
    if success_results:
        best = min(success_results, key=lambda x: x["response_time"])
        report_lines.append(f"推薦交易所: {best['name']} (最快: {best['response_time']:.0f}ms)")
    
    report_lines.append("=" * 65)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    
    print(f"\n📄 報告已保存: {filename}")
    print(f"⏱️  結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n測試被中斷")
    except Exception as e:
        print(f"\n測試錯誤: {e}")
