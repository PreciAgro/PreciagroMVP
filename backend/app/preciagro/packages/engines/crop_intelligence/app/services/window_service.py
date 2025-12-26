from __future__ import annotations

from typing import Dict, List, Optional


WINDOWS: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    "maize": {
        "zimbabwe_nr1": {"planting": ["Nov 1", "Dec 15"], "harvest": ["Apr 1", "May 31"]},
        "poland_central": {"planting": ["Apr 15", "May 20"], "harvest": ["Sep 10", "Oct 15"]},
    },
    "wheat": {
        "poland_central": {"planting": ["Sep 15", "Oct 20"], "harvest": ["Jul 5", "Aug 10"]},
    },
    "potato": {
        "poland_central": {"planting": ["Apr 10", "May 15"], "harvest": ["Aug 25", "Oct 1"]},
    },
}

DEFAULT_WINDOWS = {"planting": ["Nov 1", "Dec 1"], "harvest": ["Mar 15", "May 1"]}


class WindowService:
    def lookup(self, crop: str, region: Optional[str]) -> Dict[str, List[str]]:
        crop_key = (crop or "").lower()
        region_key = (region or "").lower() if region else None
        crop_windows = WINDOWS.get(crop_key)
        if not crop_windows:
            return DEFAULT_WINDOWS
        if region_key and region_key in crop_windows:
            return crop_windows[region_key]
        # return first entry
        first = next(iter(crop_windows.values()))
        return first


window_service = WindowService()
