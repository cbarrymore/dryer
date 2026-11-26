from dryer.discover import is_test_file, iter_source_files, language_of
from dryer.extract import entries_in_source
from dryer.scan import find_duplicates


def forms(source: str, file: str = "a.cs"):
    found, warning = entries_in_source("csharp", source, file, file)
    assert warning is None
    return found


def score(left: str, right: str) -> float:
    found = find_duplicates(forms(left, "a.cs") + forms(right, "b.cs"), threshold=0.0)
    assert len(found) == 1
    return found[0].score


LEFT = """\
namespace Demo;
public class Left {
  public async Task<int[]> Alpha(int[] xs) {
    var ys = await _repo.GetAsync<User>(xs, "a");
    return ys?.Where(y => y.Id > 0).Select(Map).ToArray() ?? [];
  }
}
"""

RIGHT = """\
namespace Other {
  internal sealed class Right {
    private async Task<int[]> Beta(int[] items) {
      var kept = await _store.GetAsync<Order>(items, 42);
      return kept?.Where(k => k.Total > 0).Select(Map).ToArray() ?? [];
    }
  }
}
"""


def test_renamed_locals_fields_and_literals_score_one():
    assert score(LEFT, RIGHT) == 1.0


def test_a_generic_callee_keeps_its_name():
    other = LEFT.replace("GetAsync<User>", "FindAsync<User>")
    names = " ".join(forms(LEFT)[0].fingerprints)
    assert "GetAsync" in names
    assert score(LEFT, other) < 1.0


def test_an_object_initializer_is_part_of_the_structure():
    template = """\
class Mapper {
  Dto Map(Entity source) {
    if (source is null) return null;
    return new Dto%s;
  }
}
"""
    two = template % " { Key = source.Key, Name = source.Name }"
    renamed = template % "() { Id = source.Id, Label = source.Label }"
    one = template % " { Key = source.Key }"
    assert score(two, renamed.replace("()", "")) == 1.0
    assert score(two, one) < 1.0
    assert "Dto" in " ".join(forms(two)[0].fingerprints)


def test_methods_with_a_body_are_the_candidates():
    source = """\
public abstract class Board {
  public Board(int size) { _size = size; }
  public abstract void Draw();
  public int Size() => _size;
  public int Area() {
    int Square(int x) => x * x;
    Func<int, int> twice = x => x * 2;
    return twice(Square(_size));
  }
  public int Count { get { return _size; } }
}
public interface IShape {
  int Edges();
  int Corners() => Edges();
}
"""
    assert [(item.start_line, item.end_line) for item in forms(source)] == [
        (4, 4),
        (5, 9),
        (14, 14),
    ]


def test_generated_migration_and_test_files_are_skipped(tmp_path):
    assert language_of("src/Api/Program.cs") == "csharp"
    assert language_of("src/Api/Form1.Designer.cs") is None
    assert language_of("src/Api/Client.g.cs") is None
    assert language_of("src/Data/Migrations/20240101_Init.cs") is None
    assert is_test_file("tests/Api.UnitTests/OrderTests.cs")
    assert is_test_file("src/Api.IntegrationTest/Fixture.cs")
    assert is_test_file("src/Api/OrderServiceTests.cs")
    assert not is_test_file("src/Api/Testing.cs")
    for name in ["src/Api/Order.cs", "src/Api/obj/Debug/Order.cs", "src/Api/bin/X.cs", ".claude/worktrees/a/Order.cs"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("class Order {}\n", encoding="utf-8")
    assert [path.relative_to(tmp_path).as_posix() for path in iter_source_files([tmp_path])] == [
        "src/Api/Order.cs"
    ]
