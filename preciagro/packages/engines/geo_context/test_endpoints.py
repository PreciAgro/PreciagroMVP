#!/usr/bin/env python3
"""
GeoContext Engine Endpoint Testing Script
Tests all endpoints with comprehensive validation
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import aiohttp
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../.."))

class GeoContextEndpointTester:
    """Comprehensive endpoint testing for GeoContext Engine."""
    
    def __init__(self, base_url: str = "http://localhost:8000", jwt_token: str = None):
        self.base_url = base_url
        self.jwt_token = jwt_token
        self.test_results: List[Dict] = []
        
    def get_headers(self) -> Dict[str, str]:
        """Get headers with optional JWT token."""
        headers = {"Content-Type": "application/json"}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        return headers
    
    async def test_health_endpoint(self, session: aiohttp.ClientSession) -> Dict:
        """Test the health endpoint."""
        test_name = "Health Check"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            start_time = time.time()
            async with session.get(f"{self.base_url}/health") as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    result = {
                        "test": test_name,
                        "status": "✅ PASS",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "data": data
                    }
                    print(f"   ✅ Health check passed - {round(response_time, 2)}ms")
                    print(f"   📊 Response: {data}")
                else:
                    result = {
                        "test": test_name,
                        "status": "❌ FAIL",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "error": f"Unexpected status code: {response.status}"
                    }
                    print(f"   ❌ Health check failed - Status: {response.status}")
                    
        except Exception as e:
            result = {
                "test": test_name,
                "status": "❌ ERROR",
                "error": str(e)
            }
            print(f"   ❌ Health check error: {e}")
            
        self.test_results.append(result)
        return result
    
    async def test_fco_resolve_poland(self, session: aiohttp.ClientSession) -> Dict:
        """Test FCO resolve for Poland (Warsaw area)."""
        test_name = "FCO Resolve - Poland"
        print(f"\n🔍 Testing: {test_name}")
        
        request_data = {
            "field": {
                "type": "Polygon",
                "coordinates": [[[21.0, 52.2], [21.01, 52.2], [21.01, 52.21], [21.0, 52.21], [21.0, 52.2]]]
            },
            "date": "2025-09-05",
            "crops": ["corn", "soybeans"],
            "forecast_days": 7,
            "use_cache": True
        }
        
        try:
            start_time = time.time()
            async with session.post(
                f"{self.base_url}/api/v1/geocontext/resolve",
                headers=self.get_headers(),
                json=request_data
            ) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Validate response structure
                    required_fields = ["context_hash", "location", "climate", "soil", "calendars"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        result = {
                            "test": test_name,
                            "status": "✅ PASS",
                            "response_time_ms": round(response_time, 2),
                            "status_code": response.status,
                            "context_hash": data.get("context_hash"),
                            "location": data.get("location", {}).get("admin_l0"),
                            "et0_mm_day": data.get("climate", {}).get("et0_mm_day"),
                            "gdd_base10_ytd": data.get("climate", {}).get("gdd_base10_ytd"),
                            "validation": "All required fields present"
                        }
                        print(f"   ✅ Poland FCO resolve passed - {round(response_time, 2)}ms")
                        print(f"   📊 Context Hash: {data.get('context_hash')}")
                        print(f"   🌍 Location: {data.get('location', {}).get('admin_l0')}")
                        print(f"   🌤️ ET0: {data.get('climate', {}).get('et0_mm_day')} mm/day")
                        print(f"   📈 GDD YTD: {data.get('climate', {}).get('gdd_base10_ytd')}")
                    else:
                        result = {
                            "test": test_name,
                            "status": "❌ FAIL",
                            "response_time_ms": round(response_time, 2),
                            "status_code": response.status,
                            "error": f"Missing required fields: {missing_fields}"
                        }
                        print(f"   ❌ Missing fields: {missing_fields}")
                else:
                    error_text = await response.text()
                    result = {
                        "test": test_name,
                        "status": "❌ FAIL",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "error": f"Status {response.status}: {error_text}"
                    }
                    print(f"   ❌ Poland FCO resolve failed - Status: {response.status}")
                    print(f"   📝 Error: {error_text}")
                    
        except Exception as e:
            result = {
                "test": test_name,
                "status": "❌ ERROR",
                "error": str(e)
            }
            print(f"   ❌ Poland FCO resolve error: {e}")
            
        self.test_results.append(result)
        return result
    
    async def test_fco_resolve_zimbabwe(self, session: aiohttp.ClientSession) -> Dict:
        """Test FCO resolve for Zimbabwe (Murewa area)."""
        test_name = "FCO Resolve - Zimbabwe"
        print(f"\n🔍 Testing: {test_name}")
        
        request_data = {
            "field": {
                "type": "Polygon",
                "coordinates": [[[31.7, -17.7], [31.71, -17.7], [31.71, -17.69], [31.7, -17.69], [31.7, -17.7]]]
            },
            "date": "2025-09-05",
            "crops": ["corn", "tobacco"],
            "forecast_days": 5,
            "use_cache": False
        }
        
        try:
            start_time = time.time()
            async with session.post(
                f"{self.base_url}/api/v1/geocontext/resolve",
                headers=self.get_headers(),
                json=request_data
            ) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    result = {
                        "test": test_name,
                        "status": "✅ PASS",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "context_hash": data.get("context_hash"),
                        "location": data.get("location", {}).get("admin_l0"),
                        "elevation": data.get("location", {}).get("elevation_m"),
                        "soil_texture": data.get("soil", {}).get("texture")
                    }
                    print(f"   ✅ Zimbabwe FCO resolve passed - {round(response_time, 2)}ms")
                    print(f"   📊 Context Hash: {data.get('context_hash')}")
                    print(f"   🌍 Location: {data.get('location', {}).get('admin_l0', 'Unknown')}")
                    print(f"   ⛰️ Elevation: {data.get('location', {}).get('elevation_m', 'N/A')}m")
                else:
                    error_text = await response.text()
                    result = {
                        "test": test_name,
                        "status": "❌ FAIL",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "error": f"Status {response.status}: {error_text}"
                    }
                    print(f"   ❌ Zimbabwe FCO resolve failed - Status: {response.status}")
                    
        except Exception as e:
            result = {
                "test": test_name,
                "status": "❌ ERROR",
                "error": str(e)
            }
            print(f"   ❌ Zimbabwe FCO resolve error: {e}")
            
        self.test_results.append(result)
        return result
    
    async def test_cached_fco_retrieval(self, session: aiohttp.ClientSession, context_hash: str) -> Dict:
        """Test cached FCO retrieval."""
        test_name = "Cached FCO Retrieval"
        print(f"\n🔍 Testing: {test_name}")
        
        if not context_hash:
            result = {
                "test": test_name,
                "status": "⏭️ SKIP",
                "error": "No context hash available from previous tests"
            }
            print(f"   ⏭️ Skipped - No context hash available")
            self.test_results.append(result)
            return result
        
        try:
            start_time = time.time()
            async with session.get(
                f"{self.base_url}/api/v1/geocontext/fco/{context_hash}",
                headers=self.get_headers()
            ) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    result = {
                        "test": test_name,
                        "status": "✅ PASS",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "cached_hash": context_hash,
                        "cache_hit": True
                    }
                    print(f"   ✅ Cache retrieval passed - {round(response_time, 2)}ms")
                    print(f"   💾 Retrieved cached FCO for hash: {context_hash}")
                elif response.status == 404:
                    result = {
                        "test": test_name,
                        "status": "✅ PASS",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "cached_hash": context_hash,
                        "cache_hit": False,
                        "note": "404 is expected if cache TTL expired"
                    }
                    print(f"   ✅ Cache miss (404) - Expected if TTL expired")
                else:
                    error_text = await response.text()
                    result = {
                        "test": test_name,
                        "status": "❌ FAIL",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "error": f"Unexpected status {response.status}: {error_text}"
                    }
                    print(f"   ❌ Unexpected status: {response.status}")
                    
        except Exception as e:
            result = {
                "test": test_name,
                "status": "❌ ERROR",
                "error": str(e)
            }
            print(f"   ❌ Cache retrieval error: {e}")
            
        self.test_results.append(result)
        return result
    
    async def test_metrics_endpoint(self, session: aiohttp.ClientSession) -> Dict:
        """Test Prometheus metrics endpoint."""
        test_name = "Metrics Endpoint"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            start_time = time.time()
            async with session.get(f"{self.base_url}/metrics") as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    metrics_text = await response.text()
                    
                    # Check for expected metrics
                    expected_metrics = [
                        "geo_context_requests_total",
                        "geo_context_request_duration_seconds",
                        "geo_context_cache_operations_total"
                    ]
                    
                    found_metrics = [metric for metric in expected_metrics if metric in metrics_text]
                    
                    result = {
                        "test": test_name,
                        "status": "✅ PASS" if found_metrics else "❌ FAIL",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "metrics_found": found_metrics,
                        "metrics_missing": [m for m in expected_metrics if m not in found_metrics],
                        "total_metrics_lines": len(metrics_text.split('\n'))
                    }
                    
                    if found_metrics:
                        print(f"   ✅ Metrics endpoint passed - {round(response_time, 2)}ms")
                        print(f"   📊 Found metrics: {found_metrics}")
                        print(f"   📈 Total metrics lines: {len(metrics_text.split('\n'))}")
                    else:
                        print(f"   ❌ No expected metrics found")
                else:
                    result = {
                        "test": test_name,
                        "status": "❌ FAIL",
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "error": f"Unexpected status code: {response.status}"
                    }
                    print(f"   ❌ Metrics endpoint failed - Status: {response.status}")
                    
        except Exception as e:
            result = {
                "test": test_name,
                "status": "❌ ERROR",
                "error": str(e)
            }
            print(f"   ❌ Metrics endpoint error: {e}")
            
        self.test_results.append(result)
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all endpoint tests and return summary."""
        print("🚀 Starting GeoContext Engine Endpoint Tests")
        print(f"🔗 Base URL: {self.base_url}")
        print(f"🔑 JWT Token: {'✅ Provided' if self.jwt_token else '❌ Not provided (may cause auth failures)'}")
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Health Check
            await self.test_health_endpoint(session)
            
            # Test 2: FCO Resolve - Poland
            poland_result = await self.test_fco_resolve_poland(session)
            poland_hash = poland_result.get("context_hash")
            
            # Test 3: FCO Resolve - Zimbabwe  
            await self.test_fco_resolve_zimbabwe(session)
            
            # Test 4: Cached FCO Retrieval (using Poland hash)
            await self.test_cached_fco_retrieval(session, poland_hash)
            
            # Test 5: Metrics Endpoint
            await self.test_metrics_endpoint(session)
        
        # Generate summary
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "✅ PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "❌ FAIL"])
        error_tests = len([r for r in self.test_results if r["status"] == "❌ ERROR"])
        skipped_tests = len([r for r in self.test_results if r["status"] == "⏭️ SKIP"])
        
        avg_response_time = sum([
            r.get("response_time_ms", 0) for r in self.test_results 
            if "response_time_ms" in r
        ]) / max(1, len([r for r in self.test_results if "response_time_ms" in r]))
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "skipped": skipped_tests,
            "success_rate": round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0,
            "average_response_time_ms": round(avg_response_time, 2),
            "base_url": self.base_url,
            "test_results": self.test_results
        }
        
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print test summary."""
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        print(f"🕐 Timestamp: {summary['timestamp']}")
        print(f"🔗 Base URL: {summary['base_url']}")
        print(f"📊 Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"🔥 Errors: {summary['errors']}")
        print(f"⏭️ Skipped: {summary['skipped']}")
        print(f"📈 Success Rate: {summary['success_rate']}%")
        print(f"⚡ Avg Response Time: {summary['average_response_time_ms']}ms")
        
        print("\n📝 DETAILED RESULTS:")
        for result in summary['test_results']:
            status_icon = result['status'].split()[0]
            test_name = result['test']
            response_time = result.get('response_time_ms', 'N/A')
            print(f"  {status_icon} {test_name:<25} - {response_time}ms")
            
            if 'error' in result:
                print(f"     ⚠️ Error: {result['error']}")

async def main():
    """Main test execution."""
    # Configuration
    BASE_URL = "http://localhost:8000"
    JWT_TOKEN = None  # Set your JWT token here if needed
    
    # Run tests
    tester = GeoContextEndpointTester(BASE_URL, JWT_TOKEN)
    summary = await tester.run_all_tests()
    
    # Print results
    tester.print_summary(summary)
    
    # Save results to file
    with open("geocontext_test_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 Full results saved to: geocontext_test_results.json")
    
    # Exit with appropriate code
    if summary['failed'] > 0 or summary['errors'] > 0:
        print("\n❌ Some tests failed. Check the results above.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
