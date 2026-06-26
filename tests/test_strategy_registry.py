from trendalgo.templates.registry import (
    StrategyTemplate,
    clear_registry,
    get,
    list_templates,
    register,
)


def test_builtin_template() -> None:
    clear_registry()
    register(
        StrategyTemplate(
            id="multi-tf-example",
            module_path="src/trendalgo/strategies/runtime/multi_tf.py",
            description="test",
            timeframes=("5m", "1h"),
        )
    )
    t = get("multi-tf-example")
    assert t is not None
    assert t.timeframes == ("5m", "1h")
    assert any(x.id == "multi-tf-example" for x in list_templates())
