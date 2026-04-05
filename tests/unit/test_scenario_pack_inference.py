from omen.scenario.pack_compiler import _infer_slot_from_text

def test_infer_slot_reproduce_bug():
    # Bug: "微软联盟" should be C, but currently matches B because "联盟" is in B
    title = "微软联盟"
    description = "这是一个测试描述"
    
    # This currently returns "B" in the buggy version
    slot = _infer_slot_from_text(title, description)
    
    # It should be "C"
    assert slot == "C"

def test_infer_slot_priorities():
    # "内部联盟" should be A (Internal)
    assert _infer_slot_from_text("内部联盟", "") == "A"
    
    # "微软平台" should be C
    assert _infer_slot_from_text("微软平台", "") == "C"
    
    # "Android联盟" should be B
    assert _infer_slot_from_text("Android联盟", "") == "B"

def test_infer_slot_none():
    assert _infer_slot_from_text("未知标题", "无关键词描述") is None
