#!/usr/bin/env python3
"""
交易所API數據獲取測試腳本 - 包含Pionex版本
"""

import asyncio
import aiohttp
import time
import statistics
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
from colorama import init, Fore, Style

# 初始化顏色輸出
init(autoreset=True)

@dataclass
class TestResult:
    """測試結果數據類"""
    exchange: str
    success: bool
    response_time: float
    data_size: int
    error_type: str = ""
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class ExchangeAPITester:
    """交易所API測試器"""
    
    def __init__(self, exchange_configs: Dict):
        self.exchange_configs = exchange_configs
        self.results = []
        self.session = None
        self.test_summary = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_single_endpoint(self, exchange: str, endpoint: str) -> TestResult:
        """測試單個端點 - 增強錯誤處理"""
        if exchange not in self.exchange_configs:
            return TestResult(
                exchange=exchange,
                success=False,
                response_time=0,
                data_size=0,
                error_type="配置不存在"
            )
        
        config = self.exchange_configs[exchange]
        url = f"{config['base_url']}{config['endpoints'][endpoint]}"
        params = config.get('params', {}).copy()
        
        start_time = time.time()
        try:
            async with self.session.get(url, params=params) as response:
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status == 200:
                    data = await response.json()
                    data_size = len(str(data))
                    
                    # 驗證數據
                    is_valid = self.validate_data(exchange, data)
                    
                    return TestResult(
                        exchange=exchange,
                        success=is_valid,
                        response_time=response_time,
                        data_size=data_size,
                        error_type="" if is_valid else "數據不完整"
                    )
                else:
                    error_text = await response.text()
                    return TestResult(
                        exchange=exchange,
                        success=False,
                        response_time=response_time,
                        data_size=0,
                        error_type=f"HTTP {response.status}: {error_text[:50]}"
                    )
                    
        except asyncio.TimeoutError:
            return TestResult(
                exchange=exchange,
                success=False,
                response_time=15,
                data_size=0,
                error_type="Timeout"
            )
        except Exception as e:
            return TestResult(
                exchange=exchange,
                success=False,
                response_time=time.time() - start_time,
                data_size=0,
                error_type=f"{type(e).__name__}: {str(e)[:50]}"
            )
    
    def validate_data(self, exchange: str, data) -> bool:
        """驗證數據完整性"""
        if exchange == "binance":
            # Binance返回的是dict，檢查必要字段
            return isinstance(data, dict) and 'symbol' in data and 'lastPrice' in data
        elif exchange == "bitget":
            # Bitget返回的是dict，結構為{"code":"00000","msg":"success","data":[ {...} ]}
            return isinstance(data, dict) and data.get('code') == '00000'
        elif exchange == "pionex":
            # Pionex返回結構：{"result": true, "data": {...}}
            return isinstance(data, dict) and data.get('result') is True
        elif isinstance(data, dict):
            return len(data) > 0
        elif isinstance(data, list):
            return len(data) > 0
        return True
    
    async def run_concurrent_tests(self, exchange: str, endpoint: str, 
                                  num_requests: int = 3) -> List[TestResult]:
        """並發測試"""
        tasks = [self.test_single_endpoint(exchange, endpoint) 
                for _ in range(num_requests)]
        return await asyncio.gather(*tasks)
    
    async def test_all_exchanges(self, endpoint: str = "ticker") -> Dict:
        """測試所有交易所"""
        all_results = {}
        
        for exchange in self.exchange_configs.keys():
            print(f"{Fore.CYAN}測試 {exchange}...{Style.RESET_ALL}")
            
            results = await self.run_concurrent_tests(exchange, endpoint, 3)
            all_results[exchange] = results
            
            # 計算統計
            successful = [r for r in results if r.success]
            success_rate = len(successful) / len(results) * 100
            response_times = [r.response_time for r in successful]
            
            if response_times:
                avg_time = statistics.mean(response_times)
                min_time = min(response_times)
                max_time = max(response_times)
            else:
                avg_time = min_time = max_time = 0
            
            self.test_summary[exchange] = {
                'success_rate': success_rate,
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'total_requests': 3,
                'successful_requests': len(successful),
                'errors': [r.error_type for r in results if not r.success]
            }
            
            # 顯示結果
            color = Fore.GREEN if success_rate >= 95 else Fore.YELLOW if success_rate >= 80 else Fore.RED
            print(f"  {color}✓ 成功率: {success_rate:.1f}% | "
                  f"平均響應: {avg_time*1000:.0f}ms{Style.RESET_ALL}")
            
            # 顯示錯誤信息
            if success_rate < 100:
                errors = set(r.error_type for r in results if not r.success and r.error_type)
                for error in errors:
                    print(f"  {Fore.RED}⚠ 錯誤: {error}{Style.RESET_ALL}")
            
            await asyncio.sleep(0.3)  # 縮短延遲，因為交易所數量增加
        
        return all_results
    
    def generate_report(self) -> str:
        """生成測試報告"""
        if not self.test_summary:
            return "暫無測試數據"
        
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append(f"{Fore.MAGENTA}交易所API測試報告 (包含Pionex){Style.RESET_ALL}")
        report_lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"測試交易所數量: {len(self.test_summary)}")
        report_lines.append("=" * 70)
        
        for exchange, stats in self.test_summary.items():
            success_rate = stats['success_rate']
            color = Fore.GREEN if success_rate >= 95 else Fore.YELLOW if success_rate >= 80 else Fore.RED
            
            report_lines.append(
                f"{exchange:10} {color}{success_rate:6.1f}%{Style.RESET_ALL} | "
                f"平均: {stats['avg_response_time']*1000:5.0f}ms | "
                f"成功: {stats['successful_requests']}/{stats['total_requests']}"
            )
            
            # 顯示錯誤信息
            if stats.get('errors'):
                unique_errors = set(stats['errors'])
                for error in unique_errors:
                    if error:
                        report_lines.append(f"      {Fore.RED}錯誤: {error}{Style.RESET_ALL}")
        
        # 計算總體
        avg_success = statistics.mean([s['success_rate'] for s in self.test_summary.values()])
        avg_response = statistics.mean([s['avg_response_time'] for s in self.test_summary.values()])
        
        report_lines.append("-" * 70)
        report_lines.append(f"總體平均: 成功率 {avg_success:.1f}% | 響應時間 {avg_response*1000:.0f}ms")
        
        # 推薦最佳
        successful_exchanges = {k:v for k,v in self.test_summary.items() if v['success_rate'] > 0}
        if successful_exchanges:
            best = max(successful_exchanges.items(), 
                      key=lambda x: (x[1]['success_rate'], -x[1]['avg_response_time']))
            report_lines.append(f"🎯 推薦使用: {best[0]} (成功率: {best[1]['success_rate']:.1f}%)")
        else:
            report_lines.append("⚠️ 所有交易所測試均失敗，請檢查網絡或API配置")
            
        report_lines.append("=" * 70)
        
        return "\n".join(report_lines)

# 交易所配置 - 包含Pionex
EXCHANGE_CONFIGS = {
    "binance": {
        "base_url": "https://api.binance.com",
        "endpoints": {"ticker": "/api/v3/ticker/24hr"},
        "params": {"symbol": "BTCUSDT"}
    },
    "kucoin": {
        "base_url": "https://api.kucoin.com",
        "endpoints": {"ticker": "/api/v1/market/orderbook/level1"},
        "params": {"symbol": "BTC-USDT"}
    },
    "gateio": {
        "base_url": "https://api.gateio.ws/api/v4",
        "endpoints": {"ticker": "/spot/tickers"},
        "params": {"currency_pair": "BTC_USDT"}
    },
    "mexc": {
        "base_url": "https://api.mexc.com",
        "endpoints": {"ticker": "/api/v3/ticker/24hr"},
        "params": {"symbol": "BTCUSDT"}
    },
    "huobi": {
        "base_url": "https://api.huobi.pro",
        "endpoints": {"ticker": "/market/detail/merged"},
        "params": {"symbol": "btcusdt"}
    },
    "bitget": {
        "base_url": "https://api.bitget.com",
        "endpoints": {"ticker": "/api/spot/v1/market/ticker"},
        "params": {"symbol": "BTCUSDT"}
    },
    "okx": {
        "base_url": "https://www.okx.com/api/v5",
        "endpoints": {"ticker": "/market/ticker"},
        "params": {"instId": "BTC-USDT"}
    },
    "pionex": {
        "base_url": "https://api.pionex.com",
        "endpoints": {"ticker": "/api/v1/market/ticker"},
        "params": {"symbol": "BTC_USDT"}
    }
}

async def main():
    """主測試函數"""
    print(f"{Fore.BLUE}{'='*55}")
    print("交易所API數據獲取測試開始 (包含Pionex)")
    print(f"{'='*55}{Style.RESET_ALL}\n")
    
    async with ExchangeAPITester(EXCHANGE_CONFIGS) as tester:
        # 測試所有交易所
        await tester.test_all_exchanges("ticker")
        
        # 生成報告
        print(f"\n{Fore.BLUE}{'='*55}")
        print("測試完成")
        print(f"{'='*55}{Style.RESET_ALL}\n")
        
        report = tester.generate_report()
        print(report)
        
        # 保存報告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"exchange_api_test_report_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 報告已保存至: {filename}")

if __name__ == "__main__":
    try:
        import aiohttp
        import colorama
    except ImportError:
        print("請安裝依賴: pip install aiohttp colorama")
        exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}測試中斷{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}錯誤: {e}{Style.RESET_ALL}")
