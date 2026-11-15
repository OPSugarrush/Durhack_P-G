from needstate.evidence import supported_change


def test_mean_and_direction_must_agree():
    e=dict(buyers=30,category_buyers=20,q=.001,low=1,high=5,change=3,up=5,down=25)
    assert not supported_change(e)
    e.update(up=25,down=5)
    assert supported_change(e)
    e['category_buyers']=3
    assert not supported_change(e)
