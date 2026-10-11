from jenesboot_v2 import main


def test_main(capsys):
    main()
    assert "jenesboot-v2" in capsys.readouterr().out
