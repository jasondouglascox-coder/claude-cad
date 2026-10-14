from cadkit.bambu import parse_slice_info

SLICE_INFO = """<config><plate>
    <filament id="1" type="PLA" used_g="2.88"/>
    <filament id="3" type="PLA" used_g="5.88"/>
    <layer_filament_lists>
      <layer_filament_list filament_list="2 3" layer_ranges="0 2,14 15" />
      <layer_filament_list filament_list="3" layer_ranges="3 8" />
      <layer_filament_list filament_list="0 2" layer_ranges="9 11" />
    </layer_filament_lists>
</plate></config>"""


def test_slice_info_bands_are_split_and_one_based():
    r = parse_slice_info(SLICE_INFO)
    assert r["grams"] == {1: 2.88, 3: 5.88}
    assert r["layers"] == [((3, 4), 0, 2), ((4,), 3, 8), ((1, 3), 9, 11), ((3, 4), 14, 15)]
