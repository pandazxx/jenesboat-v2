from jenesboat_v2 import main


def test_main(capsys):
    main()
    assert "jenesboat-v2" in capsys.readouterr().out
