"""Connector/tray regressions; explicit roles must not become brackets or housings."""
import pytest
from pv3d.geometry import build_components, export_scene
from pv3d.perception import normalize_predictions
from pv3d.schemas import ManualComponent


def test_connectors_and_trays_have_distinct_semantics_near_the_inverter():
    output = normalize_predictions(
        [[20, 10, 80, 60], [30, 58, 35, 70], [10, 80, 90, 88]],
        [0.7, 0.5, 0.5], ['a solar inverter', 'an electrical connector', 'a cable tray'],
        (100, 100), scene_mode='multiple')
    assert [o['category'] for o in output] == ['cabinet', 'connector', 'cable_tray']


def test_square_neighbor_box_is_not_accepted_as_a_cable_tray():
    output = normalize_predictions([[20, 10, 80, 60], [0, 30, 20, 55]], [0.7, 0.6],
        ['a solar inverter', 'a cable tray'], (100, 100), scene_mode='multiple')
    assert [o['category'] for o in output] == ['cabinet']


def test_vertical_cable_tray_is_retained_as_structure():
    output = normalize_predictions([[90, 5, 95, 90]], [0.6], ['a cable tray'],
                                   (100, 100), scene_mode='multiple')
    assert [o['category'] for o in output] == ['cable_tray']


def test_remote_connector_candidate_is_not_part_of_the_inverter():
    output = normalize_predictions([[20, 10, 80, 50], [2, 90, 8, 98]], [0.7, 0.6],
        ['a solar inverter', 'an electrical connector'], (100, 100), scene_mode='multiple')
    assert [o['category'] for o in output] == ['cabinet']


def test_a_row_of_connectors_is_not_also_a_tray():
    output = normalize_predictions(
        [[20, 10, 80, 60], [30, 58, 35, 70], [50, 58, 55, 70], [28, 56, 64, 74]],
        [0.7, 0.5, 0.5, 0.5], ['a solar inverter', 'an electrical connector',
                              'an electrical connector', 'a cable tray'],
        (100, 100), scene_mode='multiple')
    assert [o['category'] for o in output] == ['cabinet', 'connector', 'connector']


@pytest.mark.parametrize('generic,specific,box',[
    ('an electrical cabinet', 'a cable tray', [10, 80, 90, 88]),
    ('a metal mounting bracket', 'an electrical connector', [30, 58, 35, 70]),
])
def test_specific_component_evidence_replaces_overlapping_generic_role(generic,specific,box):
    output = normalize_predictions([[20, 10, 80, 60], box, box], [0.8, 0.7, 0.5],
        ['a solar inverter', generic, specific], (100, 100), scene_mode='multiple')
    assert len(output) == 2
    assert output[1]['category'] == ('connector' if 'connector' in specific else 'cable_tray')


@pytest.mark.parametrize('category',['connector','cable_tray'])
def test_new_components_round_trip_through_contract_and_schematic_export(tmp_path,category):
    component = ManualComponent(id='new-part',category=category,label='Visible part',bbox=(0.2,0.3,0.4,0.5))
    output, _ = build_components([component.model_dump()],(100,100))
    assert output[0]['category'] == category
    export_scene(output,tmp_path/'scene.glb')
    import trimesh
    scene = trimesh.load_scene(tmp_path/'scene.glb')
    assert set(scene.graph.nodes_geometry) == {'new-part'}
