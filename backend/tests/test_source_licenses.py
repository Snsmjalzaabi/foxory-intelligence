"""Notice coverage detects dependency updates/omissions without importing code."""
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('license_review',Path(__file__).resolve().parents[2]/'scripts/review_source_licenses.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)


def test_dependency_version_change_requires_new_retained_notice():
    rows=[{'name':'typing_extensions','version':'2'}]
    old='===== Python typing-extensions 1: LICENSE =====\n'
    assert review.notice_coverage(rows,[],old)==[{'kind':'Python','name':'typing_extensions','version':'2'}]
    assert review.notice_coverage(rows,[],old.replace(' 1:',' 2:'))==[]


def test_scoped_runtime_package_is_not_covered_by_an_unrelated_notice():
    rows=[{'name':'@example/fixture','version':'1'}]
    assert review.notice_coverage([],rows,'===== npm fixture 1: LICENSE =====\n')
    assert not review.notice_coverage([],rows,'===== npm @example/fixture 1: LICENSE =====\n')
