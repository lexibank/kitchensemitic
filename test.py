def test_valid(cldf_dataset, cldf_logger):
    assert cldf_dataset.validate(log=cldf_logger)


def test_forms(cldf_dataset):
    assert len(list(cldf_dataset["FormTable"])) == 2468


def test_parameters(cldf_dataset):
    assert len(list(cldf_dataset["ParameterTable"])) == 95


def test_languages(cldf_dataset):
    assert len(list(cldf_dataset["LanguageTable"])) == 25


def test_cognates(cldf_dataset):
    assert len(list(cldf_dataset["CognateTable"])) == 2125
