#!/usr/bin/python3

import argparse
import braceexpand
import builtins
import concurrent.futures
import contextlib
import csv
import functools
import hashlib
import itertools
import io
import json5
import logging
import operator
import os
import pathlib
import pickle
import pydot
import re
import rich.logging
import rich.progress
import typing
import yattag
import yaml
import zipfile


# More can be found at https://timberapi.com/specifications/schemas/
class Spec(typing.TypedDict):
  pass


class Blueprint(typing.TypedDict):
  pass


class TemplateCollectionSpec(Spec):
  CollectionId: str
  Blueprints: list[str]


class TemplateCollectionBlueprint(Blueprint):
  TemplateCollectionSpec: TemplateCollectionSpec


class GoodSpec(Spec):
  Id: str
  DisplayNameLocKey: str
  PluralDisplayNameLocKey: str


class GoodBlueprint(Blueprint):
  GoodSpec: GoodSpec


class NeedGroupSpec(Spec):
  Id: str
  DisplayNameLocKey: str


class NeedGroupBlueprint(Blueprint):
  NeedGroupSpec: NeedGroupSpec


class NeedSpec(Spec):
  Id: str
  Order: int
  NeedGroupId: str
  DisplayNameLocKey: str


class NeedBlueprint(Blueprint):
  NeedSpec: NeedSpec


class GoodAmount(typing.TypedDict):
  Id: str
  Amount: int


class GoodAmountSpec(Spec):
  Id: str
  Amount: int


class RecipeSpec(Spec):
  Id: str
  DisplayLocKey: str
  CycleDurationInHours: float
  Ingredients: list[GoodAmount]
  Products: list[GoodAmount]
  Fuel: str
  ProducedSciencePoints: int
  CyclesFuelLasts: int


class RecipeBlueprint(Blueprint):
  RecipeSpec: RecipeSpec


# TimberAPI specific and documented at https://timberapi.com/tools/
# TODO Remove
class ToolSpec(Spec):
  Id: str
  GroupId: str
  Order: int
  NameLocKey: str
  DevMode: typing.NotRequired[bool]


class ToolBlueprint(Blueprint):
  ToolSpec: ToolSpec


# TimberAPI enhanced and documented at https://timberapi.com/tool_groups/
class BlockObjectToolGroupSpec(Spec):
  Id: str
  Order: int
  NameLocKey: str
  Icon: str
  FallbackGroup: bool
  # Added by TimberAPI
  # TODO Remove
  Type: typing.NotRequired[str]
  Layout: typing.NotRequired[str]


# from Moddable Tool Groups at https://github.com/datvm/TimberbornMods/blob/master/ConfigurableToolGroups/Specs/ParentToolGroupSpec.cs
class ParentToolGroupSpec(Spec):
  ParentIds: list[str]


# from Moddable Tool Groups at https://github.com/datvm/TimberbornMods/blob/master/ConfigurableToolGroups/Specs/ToolGroupChildrenSpec.cs
class OrderedIds:
  Id: str
  Order: int


class ToolGroupChildrenSpec(Spec):
  ChildrenGroupsIds: list[str]
  ChildrenToolsTemplateNames: list[str]
  ChildrenOrderedIds: list[str]
  ChildrenExplicitOrderedIds: list[OrderedIds]
  DoNotIncludePlaceableToolGroup: bool


class BlockObjectToolGroupBlueprint(Blueprint):
  BlockObjectToolGroupSpec: BlockObjectToolGroupSpec
  ParentToolGroupSpec: typing.NotRequired[ParentToolGroupSpec]
  ToolGroupChildrenSpec: typing.NotRequired[ToolGroupChildrenSpec]


class FactionSpec(Spec):
  Id: str
  Order: int
  DisplayNameLocKey: str
  NewGameFullAvatar: str
  TemplateCollectionIds: list[str]


class FactionBlueprint(Blueprint):
  FactionSpec: FactionSpec


class ContinuousEffectSpec(Spec):
  NeedId: str
  PointsPerHour: float


class NeedApplierEffectSpec(Spec):
  NeedId: str
  Points: float
  Probability: str


class BuildingSpec(Spec):
  BuildingCost: list[GoodAmountSpec]
  ScienceCost: int


class LabeledEntitySpec(Spec):
  DisplayNameLocKey: str


class NaturalResourceSpec(Spec):
  Order: int


class PlaceableBlockObjectSpec(Spec):
  ToolGroupId: str
  ToolOrder: int
  DevModeTool: int


class AreaNeedApplierSpec(Spec):
  ApplicationRadius: int
  Effects: NeedApplierEffectSpec


class ContinuousEffectBuildingSpec(Spec):
  Effects: list[ContinuousEffectSpec]


class RangedEffectBuildingSpec(Spec):
  EffectRadius: int


class WorkshopRandomNeedApplierSpec(Spec):
  Effects: list[NeedApplierEffectSpec]


class ConsumedGoodSpec(Spec):
  GoodId: str
  GoodPerHour: float


class GoodConsumingBuildingSpec(Spec):
  ConsumedGoods: list[ConsumedGoodSpec]
  FullInventoryWorkHours: int


class DwellingSpec(Spec):
  MaxBeavers: int
  SleepEffects: list[ContinuousEffectSpec]


class WorkplaceSpec(Spec):
  MaxWorkers: int


class ManufactorySpec(Spec):
  ProductionRecipeIds: list[str]


class MechanicalNodeSpec(Spec):
  PowerInput: int
  PowerOutput: int


class PlanterBuildingSpec(Spec):
  PlantableResourceGroup: str


class PlantableSpec(Spec):
  ResourceGroup: str
  PlantTimeInHours: float


class YielderSpec(Spec):
  Yield: GoodAmountSpec
  RemovalTimeInHours: float
  ResourceGroup: str


class CuttableSpec(Spec):
  YielderSpec: YielderSpec


class GatherableSpec(Spec):
  YieldGrowthTimeInDays: float
  YielderSpec: YielderSpec


class GrowableSpec(Spec):
  GrowthTimeInDays: float


class RuinSpec(Spec):
  YielderSpec: YielderSpec


class CropSpec(Spec):
  pass


class YieldRemovingBuildingSpec(Spec):
  ResourceGroup: str


class TemplateSpec(Spec):
  TemplateName: str


class WateredNaturalResourceSpec(Spec):
  DaysToDieDry: float


class FloodableNaturalResourceSpec(Spec):
  MinWaterHeight: int
  MaxWaterHeight: int
  DaysToDie: float


class TemplateBlueprint(typing.TypedDict):
  Id: str
  BuildingSpec: BuildingSpec
  TemplateSpec: TemplateSpec
  LabeledEntitySpec: LabeledEntitySpec
  NaturalResourceSpec: NaturalResourceSpec
  PlaceableBlockObjectSpec: PlaceableBlockObjectSpec
  ParentToolGroupSpec: typing.NotRequired[ParentToolGroupSpec]
  AreaNeedApplierSpec: AreaNeedApplierSpec
  RangedEffectBuildingSpec: RangedEffectBuildingSpec
  WorkshopRandomNeedApplierSpec: WorkshopRandomNeedApplierSpec
  GoodConsumingBuildingSpec: GoodConsumingBuildingSpec
  DwellingSpec: DwellingSpec
  WorkplaceSpec: WorkplaceSpec
  ManufactorySpec: ManufactorySpec
  MechanicalNodeSpec: MechanicalNodeSpec
  PlanterBuildingSpec: PlanterBuildingSpec
  YieldRemovingBuildingSpec: YieldRemovingBuildingSpec
  PlantableSpec: PlantableSpec
  CuttableSpec: CuttableSpec
  GatherableSpec: GatherableSpec
  RuinSpec: RuinSpec
  CropSpec: CropSpec
  GrowableSpec: GrowableSpec
  WateredNaturalResourceSpec: WateredNaturalResourceSpec
  FloodableNaturalResourceSpec: FloodableNaturalResourceSpec


class PartialBlueprint[T: Blueprint](typing.NamedTuple):
    path: pathlib.Path | zipfile.Path
    optional: bool
    specification: T


def track[T](
    description: str,
    sequence: typing.Iterable[T],
    **kwargs,
) -> typing.Iterable[T]:
  return rich.progress.track(sequence, '%-39s' % description, **kwargs)


def load_versions(directories: list[pathlib.Path], pattern: str) -> list[dict[str, typing.Any]]:
  versions: list[dict[str, typing.Any]] = []
  ids: set[str] = set()
  for directory in track('Loading versions', directories, transient=True):
    paths = []
    for pattern in ('StreamingAssets/VersionNumbers.json', 'manifest.json'):
      logging.debug(f'Scanning {directory.joinpath(pattern).resolve()}:')
      paths.extend(directory.glob(pattern, case_sensitive=False))
    if not paths:
      logging.warning('Skipping %s', directory)
      continue
    assert len(paths) == 1, f'Expected single version manifest in {directory}, found: {paths}'
    with paths[0].open('r', encoding='utf-8-sig') as f:
      try:
        doc = typing.cast(dict, json5.load(f, strict=False))
      except Exception as e:
        e.add_note(f'in {paths[0]}')
        raise
    if 'Id' not in doc:
      assert '' not in ids, f'Multiple game directories'
      ids.add('')
      logging.info('Loading version %s of %s', doc['CurrentVersion'], 'Timberborn')
    else:
      assert doc['Id'] not in ids, f'{doc['Id']} loaded twice!'
      ids.add(doc['Id'])
      logging.info('Loading version %s of %s', doc['Version'], doc['Name'])
    versions.append(doc)
  return versions


def upgrade_toolgroup_blueprints(
    blueprints: dict[str, list[PartialBlueprint[BlockObjectToolGroupBlueprint]]]
):
  # TODO: Read Fields/Forestry from ToolGroups blueprints
  toolgroups = [
    BlockObjectToolGroupBlueprint(BlockObjectToolGroupSpec=BlockObjectToolGroupSpec(
      Id='Fields',
      Order=20 - 100,
      NameLocKey='ToolGroups.FieldsPlanting',
      Icon='',
      FallbackGroup=False,
      Type='PlantingModeToolGroup',
      Layout='Blue',
    )),
    BlockObjectToolGroupBlueprint(BlockObjectToolGroupSpec=BlockObjectToolGroupSpec(
      Id='Forestry',
      Order=30 - 100,
      NameLocKey='ToolGroups.ForestryPlanting',
      Icon='',
      FallbackGroup=False,
      Type='PlantingModeToolGroup',
      Layout='Blue',
    )),
  ]
  for toolgroup in toolgroups:
    toolgroup_specs = blueprints.setdefault(toolgroup['BlockObjectToolGroupSpec']['Id'].lower(), [])
    if any(not i.optional for i in toolgroup_specs):
      logging.warning(f'Duplicate {toolgroup['BlockObjectToolGroupSpec']['Id']} ToolGroup')
      # continue
    assert not any(not i.optional for i in toolgroup_specs)
    toolgroup_specs.insert(0, PartialBlueprint(pathlib.Path('builtin'), False, toolgroup))


def upgrade_tool_blueprints(
    templates: dict[str, TemplateBlueprint],
    blueprints: dict[str, list[PartialBlueprint[ToolBlueprint]]]
):
  for tool_specs in blueprints.values():
    for _, _, doc in tool_specs:
      if 'Order' in doc['ToolSpec']:
        doc['ToolSpec']['Order'] = int(doc['ToolSpec']['Order'])
  tools: list[ToolBlueprint] = []
  for item in templates.values():
    if 'PlaceableBlockObjectSpec' in item:
      spec = item['PlaceableBlockObjectSpec']
      tool = ToolBlueprint(ToolSpec=ToolSpec(
        Id=item['Id'],  # item['TemplateSpec']['TemplateName'],
        GroupId=spec['ToolGroupId'],
        Order=spec['ToolOrder'],
        NameLocKey=item['LabeledEntitySpec']['DisplayNameLocKey'],
      ))
      if spec['DevModeTool'] == 1:
        tool['ToolSpec']['DevMode'] = True
      tools.append(tool)
    if 'PlantableSpec' in item:
      spec = item['NaturalResourceSpec']
      tools.append(ToolBlueprint(ToolSpec=ToolSpec(
        Id=item['Id'],  # item['TemplateSpec']['TemplateName'],
        GroupId='Fields' if 'CropSpec' in item else 'Forestry',
        Order=spec['Order'],
        NameLocKey=item['LabeledEntitySpec']['DisplayNameLocKey'],
      )))
  for tool in tools:
    tool_specs = blueprints.setdefault(tool['ToolSpec']['Id'].lower(), [])
    if any(not i.optional for i in tool_specs):
      logging.warning(f'Duplicate {tool['ToolSpec']['Id']} Tool')
      # continue
    assert not any(not i.optional for i in tool_specs), tool_specs
    tool_specs.insert(0, PartialBlueprint(pathlib.Path('builtin'), False, tool))


def merge_into_spec(
    name: str,
    spec: Blueprint | dict,
    json: typing.ItemsView[str, object],
):
  for k, v in json:
    k, _, m = k.partition('#')
    i = spec.get(k, None)
    if isinstance(i, list) and m:
      assert isinstance(v, list), f'{name}.{k}: {v}'
      if m == 'append':
        i.extend(v)
      elif m == 'remove':
        for x in v:
          if x not in i:
            logging.warning(f'No {x} in {name}.{k}')
            continue
          assert x in i, f'{name}.{k}: {x}'
          i.remove(x)
      else:
        # TODO: Support delete
        assert False, f'Unsupported mode: {name}.{k}#{m}: {v}'
    elif isinstance(i, dict):
      assert isinstance(v, dict), f'{name}.{k}: {v}'
      merge_into_spec(f'{name}.{k}', i, v.items())
    else:
      if type(i) == float and type(v) == int:
        logging.warning(f'{name}.{k}: {type(i)} vs {type(v)}')
        assert v == float(v), f'{name}.{k}: {type(i)} vs {type(v)}'
        v = float(v)  # upcast
      assert i is None or type(i) == type(v), f'{name}.{k}: {type(i)} vs {type(v)}'
      spec[k] = v


def get_asset_content(f: io.TextIOWrapper):
  def mono_behaviour_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return loader.construct_mapping(node)

  loader = yaml.SafeLoader(f)
  try:
    loader.add_constructor('tag:unity3d.com,2011:114', mono_behaviour_constructor)
    asset = loader.get_single_data()
  finally:
    loader.dispose()
  mono_behaviour = asset['MonoBehaviour']
  guid = mono_behaviour['m_Script']['guid']
  if guid == '13adc0e4713bee36fd631781df55c5df':  # Timberborn.BlueprintSystem.BlueprintAsset
    return mono_behaviour['_content']
  raise Exception(f'Unknown Script guid: {guid}')


def load_blueprint_jsons[T: Blueprint](
    directories: list[pathlib.Path],
    blueprint: str,
    pattern: str,
    disable_progess = False,
    upgrade_specs: typing.Callable[[dict[str, list[PartialBlueprint[T]]]], None] | None = None,
) -> list[T]:
  all_paths: list[tuple[int, pathlib.Path | zipfile.Path]] = []
  for i, directory in enumerate(directories):
    # TODO This should iterate over all files and index by available Specs instead
    pattern_dir = '' if i else f'StreamingAssets/Modding/Blueprints.zip'
    pattern_path = autoPath(directory.joinpath(pattern_dir))
    logging.debug(f'Scanning {pattern_path.joinpath(pattern)}:')
    paths = list(pattern_path.glob(pattern))
    # if i and blueprint == 'BlockObjectToolGroup':  # HACK Handle alternate filenames for TimberAPI
    #   pattern = f'**/TimberApiToolGroup.*.blueprint.json'
    #   logging.debug(f'Scanning {directory.joinpath(pattern)}:')
    #   paths.extend(pattern_path.glob(pattern))
    if i and blueprint == 'BlockObjectToolGroup':  # HACK Handle alternative filenames for Whitepaws
      pattern2 = f'**/{pattern.replace('BlockObjectToolGroup', 'ToolGroup')}'
      paths.extend(pattern_path.glob(pattern2))
    if i and not paths:  # HACK to find exported assets for Emberpelts
      pattern2 = f'**/{pattern.replace('.blueprint.json', '.blueprint.asset')}'
      paths.extend(pattern_path.glob(pattern2))
    if i and not paths:  # HACK to find blueprints for Emberpelts BlockObjectToolGroups
      pattern2 = f'**/{pattern.replace(blueprint, f'{blueprint}s')}'
      paths.extend(pattern_path.glob(pattern2))
    if i and not paths:  # HACK to find blueprints for 1x1x2Storage
      pattern2 = f'**/{pattern.replace('.json', '.blueprint.json')}'
      paths.extend(pattern_path.glob(pattern2))
    if i and not paths:  # HACK to find exported assets for Staircase
      pattern2 = f'**/{pattern.replace('.json', '.blueprint.asset')}'
      paths.extend(pattern_path.glob(pattern2))
    all_paths.extend((i, path) for path in paths)
  assert all_paths or upgrade_specs, f'No blueprints found for {pattern}'

  all_specs: dict[str, list[PartialBlueprint[T]]] = {}
  for i, p in track(f'Loading {blueprint} blueprints', all_paths, total=len(all_paths), disable=disable_progess):
    logging.debug(f'Reading {p}')
    blueprint_name, _, name = p.stem.lower().partition('.')
    # assert blueprint_name == blueprint.lower().partition('.')[0], f'{blueprint_name} == {blueprint.lower().partition('.')[0]}'
    assert (
      blueprint_name == blueprint.lower().partition('.')[0] + 's' or  # HACK for Emberpelts
      blueprint_name == blueprint.lower().partition('.')[0].replace('blockobjecttoolgroup', 'toolgroup') or  # HACK for Whitepaws
      blueprint_name == blueprint.lower().partition('.')[0]
    ), f'{blueprint_name} == {blueprint.lower().partition('.')[0]}'
    optional = name.endswith('.optional.blueprint')
    name = name.replace('.optional', '')
    with p.open('r', encoding='utf-8-sig') as f:
      try:
        if p.suffix.lower().endswith('.asset'):
          doc = typing.cast(T, json5.loads(get_asset_content(f), strict=False))
        else:
          doc = typing.cast(T, json5.load(f, strict=False))
      except Exception as e:
        e.add_note(f'in {p}')
        raise
    all_specs.setdefault(name, []).append(PartialBlueprint(p, optional, doc))
  if upgrade_specs:
    upgrade_specs(all_specs)

  merged_specs: dict[str, T] = {}
  for name, l in all_specs.items():
    for p, optional, doc in sorted(l, key=lambda i: (i.optional)):
      if optional:
        if name not in merged_specs:
          logging.debug(f'Skipping optional {p}')
          continue
        # assert name in merged_specs, name
      spec = merged_specs.setdefault(name, typing.cast(T, dict()))
      merge_into_spec(name, spec, doc.items())

  return [s for s in merged_specs.values()]


def load_blueprints[T: Blueprint](
    directories: list[pathlib.Path],
    cls: type[T],
    upgrade_specs: typing.Callable[[dict[str, list[PartialBlueprint[T]]]], None] | None = None,
) -> list[T]:
  blueprint = cls.__name__.removesuffix('Blueprint')
  return load_blueprint_jsons(
    directories,
    blueprint,
    f'**/{blueprint}.*.blueprint.json',
    upgrade_specs=upgrade_specs,
  )


def load_template(
    directories: list[pathlib.Path],
    file_path: str,
) -> TemplateBlueprint:
  blueprint = pathlib.PurePath(file_path).stem
  templates = load_blueprint_jsons(
    directories,
    blueprint,
    f'{file_path}.json',
    disable_progess=True,
  )
  assert len(templates) == 1
  return typing.cast(TemplateBlueprint, dict(Id=blueprint, **templates[0]))


def load_templates_and_tools(
    directories: list[pathlib.Path],
    factions: dict[str, FactionBlueprint],
    debug: bool,
) -> tuple[dict[str, dict[str, TemplateBlueprint]], dict[str, list[ToolBlueprint]]]:
  map = builtins.map if debug else concurrent.futures.ProcessPoolExecutor().map
  templates: dict[str, dict[str, TemplateBlueprint]] = {'common': {}}
  tools: dict[str, list[ToolBlueprint]] = {}

  template_collections = load_blueprints(directories, TemplateCollectionBlueprint)
  commonpaths = list(itertools.chain.from_iterable(
    typing.cast(list, b['TemplateCollectionSpec']['Blueprints']) for b in template_collections if b['TemplateCollectionSpec']['CollectionId'].lower() == 'common'))

  for template in track(f'Loading common templates', map(load_template, *zip(*((directories, template) for template in commonpaths))), total=len(commonpaths)):
    assert template and template['Id'].lower() not in templates['common']
    templates['common'][template['Id'].lower()] = template
  tools['common'] = load_blueprints(directories, ToolBlueprint, functools.partial(upgrade_tool_blueprints, templates['common']))

  for key, faction in factions.items():
    if faction['FactionSpec']['NewGameFullAvatar'].endswith('NO'):
      logging.warning(f'Skipping {faction['FactionSpec']['Id']} because avatar ends with NO')
      continue

    faction_collections = tuple(g.lower() for g in faction['FactionSpec']['TemplateCollectionIds'])
    faction_templates = list(itertools.chain.from_iterable(
      typing.cast(list, b['TemplateCollectionSpec']['Blueprints']) for b in template_collections if b['TemplateCollectionSpec']['CollectionId'].lower() in faction_collections))
    templates[key] = {}
    for template in track(f'Loading {faction['FactionSpec']['Id']} templates', map(load_template, *zip(*((directories, template) for template in faction_templates))), total=len(faction_templates)):
      assert template
      assert template['Id'].lower() not in templates[key], template['Id']
      if template['Id'].lower() in templates[key]:
        breakpoint()
      templates[key][template['Id'].lower()] = template
    tools[key] = load_blueprints(directories, ToolBlueprint, functools.partial(upgrade_tool_blueprints, templates[key]))
  return templates, tools


def load_translations(directories: list[pathlib.Path], language: str):
  csv.register_dialect('timberborn', skipinitialspace=True)  # HACK: , strict=True)  # Work around for bad escaping in enUS Demolishable.Science.Grants
  catalog: dict[str, str] = {}
  for i, directory in enumerate(directories):
    pattern_dir = f'Localizations' if i else f'StreamingAssets/Modding/Localizations.zip'
    pattern_path = autoPath(directory.joinpath(pattern_dir))
    patterns = [f'{language}{suffix}' for suffix in ['*.txt', '*.csv']]
    paths: list[pathlib.Path] = []
    for pattern in patterns:
      paths.extend(pathlib.Path(str(p)).relative_to(str(pattern_path)) for p in pattern_path.glob(pattern))
    # assert len(paths) <= 1, f'len(glob({pattern})) == {len(paths)}: {paths}'
    for x in paths:
      loc_path = pattern_path.joinpath(x)
      with loc_path.open('r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, dialect='timberborn')
        try:
          for row in reader:
            if not i and row['ID'] in catalog:
              logging.warning(f'Duplicate key {row['ID']!r} on line {reader.line_num} of {loc_path}')
              # For duplicate key in WB en_US
              assert row['ID'] not in catalog, f'Duplicate key {row['ID']!r} on line {reader.line_num} of {loc_path}'
            catalog[row['ID']] = row['Text']
        except Exception as e:
          e.add_note(f'Loading {loc_path} on line {reader.line_num}')
          raise

  catalog['Pictogram.Dwellers'] = '🛌'
  catalog['Pictogram.Workers'] = '🦫'
  catalog['Pictogram.Power'] = '⚡'
  catalog['Pictogram.Science'] = '⚛️'
  catalog['Pictogram.Grows'] = '🌱'
  catalog['Pictogram.Dehydrates'] = '☠️'
  catalog['Pictogram.Drowns'] = '🌊'
  catalog['Pictogram.Matures'] = '🧺'
  catalog['Pictogram.Aquatic'] = '💦'
  catalog['Pictogram.Plantable'] = '🌱'
  catalog['Pictogram.Cuttable'] = '🪚'
  catalog['Pictogram.Gatherable'] = '🧺'
  catalog['Pictogram.Ruin'] = '⛓️'

  catalog['Time.DaysShort'] = catalog['Time.DaysShort'].format('{:g}')
  catalog['Time.HoursShort'] = catalog['Time.HoursShort'].format('{:g}')

  def gettext(message: str):
    if message in catalog:
      return catalog[message]
    if message.endswith('DisplayName'):
      suffix = 's' if message.endswith('PluralDisplayName') else ''
      guess = message.rpartition('.')[0].partition('.')[2]
      return f'Untranslated: {guess}{suffix}'
    return f'Untranslated: {message}'

  return gettext


def dict_group_by_id[T](iterable: typing.Iterable[T], key: str) -> dict[str, list[T]]:
  """Groups an interable of dicts into a dict of lists by the provided key."""
  groups: dict[str, list[T]] = {}
  for value in iterable:
    group = typing.cast(dict, value)
    for key_part in key.split('.'):
      if key_part not in group:
        group = ''
        break
      group = typing.cast(dict, group)[key_part]
    if type(group) == list:
      for item in group:
        item = typing.cast(str, item).lower()
        groups.setdefault(item, []).append(value)
    else:
      group = typing.cast(str, group).lower()
      groups.setdefault(group, []).append(value)
  return groups


class Cell(typing.TypedDict):
  Faction: FactionBlueprint
  FactionName: str
  Links: dict[str, str]


class Index():

  def __init__(
      self,
      args: argparse.Namespace,
  ):
    self.args = args
    self.items: dict[str, dict[str, Cell]] = {}

  def AddItem(self, gettext, faction: FactionBlueprint, txt: str, filename: str):
    lang = self.items.setdefault(gettext('Settings.Language.Name'), {})
    cell = lang.setdefault(faction['FactionSpec']['Id'], Cell(
      Faction=faction,
      FactionName=gettext(faction['FactionSpec']['DisplayNameLocKey']),
      Links={},
    ))
    cell['Links'][filename] = txt

  def Write(self, filename, versions):
    self.stack = [[]]
    doc = yattag.Doc()
    doc.asis('<!DOCTYPE html>')
    with doc.tag('html'):
      with doc.tag('head'):
        with doc.tag('meta', charset='utf-8'):
          pass
        with doc.tag('meta', name='viewport', content='width=device-width, initial-scale=1'):
          pass
        doc.line('title', 'Timbertrees')
        if self.args.src_link:
          with doc.tag('link', href='../style.css', rel='stylesheet'):
            pass
        else:
          with doc.tag('style'):
            with open('style.css', 'r', encoding='utf-8-sig') as f:
              doc.asis('\n' + f.read())
      with doc.tag('body'):
        doc.line('h1', 'Timbertrees')
        with doc.tag('table'):
          for lang, factions in self.items.items():
            with doc.tag('tr'):
              doc.line('th', lang)
              for cell in factions.values():
                with doc.tag('td', klass='name'):
                  for dst, txt in cell['Links'].items():
                    doc.line('a', txt, href=pathlib.Path(dst).name)
                    doc.text(' ')
        with doc.tag('script'):
          doc.asis(f'var manifests = {json5.dumps(versions, indent=2, trailing_commas=False)};')
    with open(filename, 'w', encoding='utf-8') as f:
      print(yattag.indent(doc.getvalue()), file=f)


class Generator:

  def __init__(
      self,
      args: argparse.Namespace,
      index: Index,
      gettext: typing.Callable[[str, ], str],
      faction: FactionBlueprint,
      goods: dict[str, GoodBlueprint],
      needgroups: dict[str, NeedGroupBlueprint],
      needs: dict[str, NeedBlueprint],
      recipes: dict[str, RecipeBlueprint],
      toolgroups: dict[str, BlockObjectToolGroupBlueprint],
      tools: dict[str, ToolBlueprint],
      templates: dict[str, TemplateBlueprint],
  ):
    self.args = args
    self.index = index
    self.gettext = gettext
    self.faction = faction
    self.goods = goods
    self.needgroups = needgroups
    self.needs = needs
    self.recipes = recipes
    self.toolgroups = toolgroups
    # TODO Handle ToolGroupChildrenSpec
    self.toolgroups_by_group = dict_group_by_id(toolgroups.values(), 'ParentToolGroupSpec.ParentIds')
    # TODO Handle ParentToolGroupSpec and ToolGroupChildrenSpec
    self.tools_by_group = dict_group_by_id(tools.values(), 'ToolSpec.GroupId')
    self.templates = {template['Id'].lower(): template for template in templates.values() if 'TemplateSpec' in template}
    self.natural_resources: list[TemplateBlueprint] = sorted(
      [p for p in self.templates.values() if 'NaturalResourceSpec' in p],
      key=lambda p: ('CropSpec' not in p, p['NaturalResourceSpec']['Order'])
    )
    self.plantable_by_group = dict_group_by_id(self.natural_resources, 'PlantableSpec.ResourceGroup')
    self.planter_building_by_group = dict_group_by_id(self.templates.values(), 'PlanterBuildingSpec.PlantableResourceGroup')
    cuttable_by_group = dict_group_by_id(self.natural_resources, 'CuttableSpec.YielderSpec.ResourceGroup')
    gatherable_by_group = dict_group_by_id(self.natural_resources, 'GatherableSpec.YielderSpec.ResourceGroup')
    scavengable_by_group = dict_group_by_id(self.templates.values(), 'RuinSpec.YielderSpec.ResourceGroup')
    self.yieldable_by_group: dict[
      str,
      tuple[typing.Literal['CuttableSpec'], list[TemplateBlueprint]] |
      tuple[typing.Literal['GatherableSpec'], list[TemplateBlueprint]] |
      tuple[typing.Literal['RuinSpec'], list[TemplateBlueprint]]
    ] = {}
    self.yieldable_by_group.update({k: ('CuttableSpec', v) for k, v in cuttable_by_group.items()})
    self.yieldable_by_group.update({k: ('GatherableSpec', v) for k, v in gatherable_by_group.items()})
    self.yieldable_by_group.update({k: ('RuinSpec', v) for k, v in scavengable_by_group.items()})

  def RenderFaction(self, faction: FactionBlueprint):
    self.RenderNaturalResources(self.natural_resources)
    for b in self.toolgroups_by_group['']:
      if b['BlockObjectToolGroupSpec'].get('Type') != 'PlantingModeToolGroup':
        self.RenderToolGroup(b)

  def RenderNaturalResources(self, resources: list[TemplateBlueprint]):
    for b in self.toolgroups_by_group['']:
      if b['BlockObjectToolGroupSpec'].get('Type') == 'PlantingModeToolGroup':
        self.RenderToolGroup(b)

  def RenderToolGroup(self, toolgroup: BlockObjectToolGroupBlueprint):
    items: list[tuple[int, typing.Literal[True], BlockObjectToolGroupBlueprint] | tuple[int, typing.Literal[False], ToolBlueprint]] = []
    for tool in self.tools_by_group.get(toolgroup['BlockObjectToolGroupSpec']['Id'].lower(), []):
      items.append((tool['ToolSpec']['Order'], False, tool))
    for tg in self.toolgroups_by_group.get(toolgroup['BlockObjectToolGroupSpec']['Id'].lower(), []):
      items.append((tg['BlockObjectToolGroupSpec']['Order'], True, tg))

    for _, is_group, item in sorted(items, key=lambda x: (x[0], x[1])):
      if is_group:
        toolgroup = typing.cast(BlockObjectToolGroupBlueprint, item)
        self.RenderToolGroup(toolgroup)
      else:
        tool = typing.cast(ToolBlueprint, item)
        if tool['ToolSpec'].get('DevMode'):
          logging.debug(f'Skipping DevMode Tool {tool['ToolSpec']['Id']}')
          continue
        template = self.templates[tool['ToolSpec']['Id'].lower()]
        if 'PlantableSpec' in template:
          self.RenderNaturalResource(template)
        if 'PlaceableBlockObjectSpec' in template:
          self.RenderBuilding(template)

  def RenderBuilding(self, building: TemplateBlueprint):
    for r in building.get('ManufactorySpec', {}).get('ProductionRecipeIds', []):
      if r.lower() not in self.recipes:
        logging.warning(f'Skipping missing recipe: {r}')
        continue
      self.RenderRecipe(self.recipes[r.lower()])

  def RenderNaturalResource(self, resource: TemplateBlueprint): ...
  def RenderRecipe(self, recipe: RecipeBlueprint): ...
  def Write(self, filename): ...


class GraphGenerator(Generator):

  FONTSIZE = 28

  def dottext(self, message):
    message = self.gettext(message)
    message = re.sub(r'<color=(\w+)>(.*?)</color>', r'<font color="\1">\2</font>', message, flags=re.S)
    if message.startswith('<') and message.endswith('>'):
      message = f'<{message}>'
    return message

  def RenderFaction(self, faction: FactionBlueprint, templates: typing.Collection[TemplateBlueprint], toolgroups: dict[str, BlockObjectToolGroupBlueprint] ):
    _ = self.dottext

    self.graph.set_name(faction['FactionSpec']['Id'])
    self.graph.set_label(_(faction['FactionSpec']['DisplayNameLocKey']))  # type: ignore
    self.graph.add_node(pydot.Node(
      'SciencePoints',
      label=_('Science.SciencePoints'),
      # image='sprites/bottombar/buildinggroups/Science.png',
    ))

    for building in templates:
      if building.get('PlaceableBlockObjectSpec', {}).get('ToolGroupId', '').lower() not in toolgroups:
        continue
      toolgroup = toolgroups[building['PlaceableBlockObjectSpec']['ToolGroupId'].lower()]

      building_goods = set()
      for c in building.get('BuildingSpec', {}).get('BuildingCost', []):
        building_goods.add(c['Id'].lower())

      recipes = building.get('ManufactorySpec', {}).get('ProductionRecipeIds', [])
      for r in recipes:
        sg = pydot.Subgraph(
          building['Id'] + ('.' + r if len(recipes) > self.args.graph_grouping_threshold else ''),
          cluster=True,
          label=f'[{_(toolgroup['BlockObjectToolGroupSpec']['NameLocKey'])}]\n{_(building['LabeledEntitySpec']['DisplayNameLocKey'])}',
          fontsize=self.FONTSIZE,
        )
        self.graph.add_subgraph(sg)

        if r.lower() not in self.recipes:
          logging.warning(f'Skipping missing recipe: {r}')
          continue
        self.RenderRecipe(sg, building, building_goods, self.recipes[r.lower()])

  def RenderRecipe(self, sg, building, building_goods, recipe: RecipeBlueprint):
    _ = self.dottext

    sg.add_node(pydot.Node(
      building['Id'] + '.' + recipe['RecipeSpec']['Id'],
      label=f'{_('Time.HoursShort').format(recipe['RecipeSpec']['CycleDurationInHours'])}',
      tooltip=_(recipe['RecipeSpec']['DisplayLocKey']),
    ))

    if recipe['RecipeSpec']['Fuel']:
      good = self.goods[recipe['RecipeSpec']['Fuel'].lower()]
      amount = round(1 / recipe['RecipeSpec']['CyclesFuelLasts'], 3)
      self.graph.add_edge(pydot.Edge(
        good['GoodSpec']['Id'],
        building['Id'] + '.' + recipe['RecipeSpec']['Id'],
        label=amount,
        labeltooltip=f'{_(good['GoodSpec']['DisplayNameLocKey' if amount == 1 else 'PluralDisplayNameLocKey'])} --> {_(recipe['RecipeSpec']['DisplayLocKey'])}',
        style='dashed' if good['GoodSpec']['Id'].lower() in building_goods else 'solid',
        color='#b30000',
      ))

    for x in recipe['RecipeSpec']['Ingredients']:
      if x['Id'].lower() not in self.goods:
        continue
      good = self.goods[x['Id'].lower()]
      #if good['Id'].lower() in building_goods:
      #  continue
      self.graph.add_node(pydot.Node(
        good['GoodSpec']['Id'],
        label=_(good['GoodSpec']['DisplayNameLocKey']),
        # image=f'sprites/goods/{good['Good']['Id']}Icon.png',
      ))
      self.graph.add_edge(pydot.Edge(
        good['GoodSpec']['Id'],
        building['Id'] + '.' + recipe['RecipeSpec']['Id'],
        label=x['Amount'],
        labeltooltip=f'{_(good['GoodSpec']['DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'])} --> {_(recipe['RecipeSpec']['DisplayLocKey'])}',
        style='dashed' if good['GoodSpec']['Id'].lower() in building_goods else 'solid',
        color='#b30000',
      ))

    for x in recipe['RecipeSpec']['Products']:
      if x['Id'].lower() not in self.goods:
        continue
      good = self.goods[x['Id'].lower()]
      self.graph.add_node(pydot.Node(
        good['GoodSpec']['Id'],
        label=_(good['GoodSpec']['DisplayNameLocKey']),
        # image=f'sprites/goods/{good['Good']['Id']}Icon.png',
      ))
      self.graph.add_edge(pydot.Edge(
        building['Id'] + '.' + recipe['RecipeSpec']['Id'],
        good['GoodSpec']['Id'],
        label=x['Amount'],
        color='#008000',
      ))

    if recipe['RecipeSpec']['ProducedSciencePoints'] > 0:
      self.graph.add_edge(pydot.Edge(
        building['Id'] + '.' + recipe['RecipeSpec']['Id'],
        'SciencePoints',
        label=recipe['RecipeSpec']['ProducedSciencePoints'],
        color='#008000',
      ))

  def Write(self, filename):

    self.graph = g = pydot.Dot(
      graph_type='digraph',
      tooltip=' ',
      labelloc='t',
      fontsize=self.FONTSIZE * 1.5,
      rankdir='LR',
      # ratio=9 / 16,
      penwidth=2,
      bgcolor='#1d2c38',
      color='#a99262',
      fontcolor='white',
      style='filled',
      fillcolor='#322227',
      # clusterrank='none',
      # newrank=True,
      # concentrate=True,
    )

    g.set_node_defaults(
      tooltip=' ',
      fontsize=self.FONTSIZE,
      penwidth=2,
      color='#a99262',
      fontcolor='white',
      fillcolor='#22362a',
      style='filled',
    )
    g.set_edge_defaults(
      tooltip=' ',
      labeltooltip=' ',
      fontsize=self.FONTSIZE,
      penwidth=2,
      color='#a99262',
      fontcolor='white',
    )

    self.RenderFaction(self.faction, self.templates.values(), self.toolgroups)

    self.graph.write(f'{filename}.dot', format='raw', encoding='utf-8')
    self.graph.write(f'{filename}.svg', format='svg', encoding='utf-8')

    self.index.AddItem(self.gettext, self.faction, '[svg]', f'{filename}.svg')


class HtmlGenerator(Generator):

  style: str = ''
  script: str = ''

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if not self.style:
      logging.debug('Loading style.css')
      with open('style.css', 'r', encoding='utf-8-sig') as f:
        type(self).style = f.read()
    if not self.script:
      logging.debug('Loading script.js')
      with open('script.js', 'r', encoding='utf-8-sig') as f:
        type(self).script = f.read()

  class Header:
    def __init__(self, doc: yattag.Doc):
      self.doc = doc
      self.end = len(doc.result)

    @contextlib.contextmanager
    def tag(
      self,
      tag_name: str,
      *args: tuple[str, str | int | float],
      **kwargs: str | int | float,
    ) -> typing.Generator[None, None, None]:
      with self.doc.tag(tag_name, *args, **kwargs):
        yield
      self.end = len(self.doc.result)

    def line(
      self,
      tag_name: str,
      text_content: str,
      *args: tuple[str, str | int | float],
      **kwargs: str | int | float,
    ):
      self.doc.line(tag_name, text_content, *args, **kwargs)
      self.end = len(self.doc.result)

  @contextlib.contextmanager
  def tag(
    self,
    tag_name: str,
    *args: tuple[str, str | int | float],
    **kwargs: str | int | float,
  ) -> typing.Generator[Header, None, None]:
    doc = self.doc
    t = doc.tag(tag_name, *args, **kwargs)

    start = len(doc.result)
    with t:
      header = self.Header(doc)
      yield header
      end = len(doc.result)
    if end == header.end:
      del doc.result[start:]

  def RenderFaction(self, faction: FactionBlueprint, filename: pathlib.Path):
    _ = self.gettext
    tag = self.doc.tag
    line = self.doc.line
    name = _(faction['FactionSpec']['DisplayNameLocKey'])
    with tag('head'):
      with tag('meta', charset='utf-8'):
        pass
      with tag('meta', name='viewport', content='width=device-width, initial-scale=1'):
        pass
      line('title', name)
      if self.args.src_link:
        with tag('link', href='../style.css', rel='stylesheet'):
          pass
        with tag('script', src='../script.js'):
          pass
      else:
        with tag('style'):
          self.doc.asis('\n' + self.style)
        with tag('script'):
          self.doc.asis('\n' + self.script)
    with tag('body'):
      line('h1', name)
      with self.tag('div', id='content', klass='card'):
        with self.tag('div', klass='filters'):
          with self.tag('div', id='toggle'):
            line('span', '▲ ◀', klass='producers')
            line('span', ' / ')
            line('span', '▼ ▶', klass='consumers')
            line('span', ' / *')
        super().RenderFaction(faction)
      # with tag('object', width='1440', data=str(filename.relative_to(filename.parent).with_suffix('.svg'))):
      #   pass

  def RenderNaturalResources(self, resources: list[TemplateBlueprint]):
    _ = self.gettext
    line = self.doc.line
    with self.tag('div', klass='toolgroup card'):
      line('div', _('MapEditor.Layers.NaturalResources'), klass='name')
      with self.tag('table'):
        with self.tag('tr'):
          line('th', '', klass='name')
          line('th', '', klass='name')
          line('th', _(f'Pictogram.Grows'))
          line('th', _(f'Pictogram.Dehydrates'))
          line('th', _(f'Pictogram.Drowns'))
          line('th', _(f'Pictogram.Matures'))
        super().RenderNaturalResources(resources)

  def RenderNaturalResource(self, r: TemplateBlueprint):
    _ = self.gettext
    line = self.doc.line
    plantable = r.get('PlantableSpec')
    searchable = [r['Id'].lower()]
    for yield_type in ('CuttableSpec', 'GatherableSpec', 'RuinSpec'):
      if yield_type in r:
        item = r[yield_type]['YielderSpec']['Yield']['Id'].lower()
        if item != 'log' and item not in searchable:
          searchable.append(item)
    with self.tag('tr', ('data-searchable', ' '.join(searchable)), ('data-category', 'producer'), klass='naturalresource'):
      line('td', _(f'Pictogram.Aquatic') if r['FloodableNaturalResourceSpec']['MinWaterHeight'] > 0 else '', klass='name')
      line('td', _(r['LabeledEntitySpec']['DisplayNameLocKey']), klass='name')
      line('td', f'{_('Time.DaysShort').format(r['GrowableSpec']['GrowthTimeInDays'])}')
      line('td', f'{_('Time.DaysShort').format(r['WateredNaturalResourceSpec']['DaysToDieDry'])}')
      line('td', f'{_('Time.DaysShort').format(r['FloodableNaturalResourceSpec']['DaysToDie'])}')
      if 'GatherableSpec' in r:
        line('td', f'{_('Time.DaysShort').format(r['GatherableSpec']['YieldGrowthTimeInDays'])}')
      else:
        line('td', '')

      super().RenderNaturalResource(r)

  def RenderToolGroup(self, toolgroup: BlockObjectToolGroupBlueprint):
    _ = self.gettext
    line = self.doc.line
    if toolgroup['BlockObjectToolGroupSpec'].get('Type') == 'PlantingModeToolGroup':
      super().RenderToolGroup(toolgroup)
      return
    with self.tag('div', klass='toolgroup card') as header:
      header.line('div', _(toolgroup['BlockObjectToolGroupSpec']['NameLocKey']), klass='name')
      super().RenderToolGroup(toolgroup)

  def RenderBuilding(self, building: TemplateBlueprint):
    _ = self.gettext
    line = self.doc.line
    with self.tag('div', klass='building card'):
      name = _(building['LabeledEntitySpec']['DisplayNameLocKey']).replace('\n', ' ')
      line('div', name, klass='name')
      with self.tag('div', klass='stats'):
        if building['BuildingSpec']['ScienceCost'] > 0:
          science = building['BuildingSpec']['ScienceCost']
          if science >= 1000:
            science = f'{science / 1000:n}k'
          line('div', f'{science}{_(f'Pictogram.Science')}', klass='science')
        if 'DwellingSpec' in building:
          line('div', f'{building['DwellingSpec']['MaxBeavers']}{_(f'Pictogram.Dwellers')}', klass='dwelling')
        if 'WorkplaceSpec' in building:
          line('div', f'{building['WorkplaceSpec']['MaxWorkers']}{_(f'Pictogram.Workers')}', klass='workers')
        if 'MechanicalNodeSpec' in building and building['MechanicalNodeSpec']['PowerInput'] > 0:
          line('div', f'{building['MechanicalNodeSpec']['PowerInput']}{_(f'Pictogram.Power')}', klass='power')

      with self.tag('div', klass='content'):
        with self.tag('ul', klass='cost'):
          for x in building['BuildingSpec']['BuildingCost']:
            good = self.goods[x['Id'].lower()]
            amount = x['Amount']
            lockey = 'DisplayNameLocKey' if amount == 1 else 'PluralDisplayNameLocKey'
            label = _(good['GoodSpec'][lockey])
            line('li', f'{amount} {label}', ('data-searchable', good['GoodSpec']['Id'].lower()), ('data-category', 'consumer'))

          if 'GoodConsumingBuildingSpec' in building:
            for x in building['GoodConsumingBuildingSpec']['ConsumedGoods']:
              good = self.goods[x['GoodId'].lower()]
              amount = x['GoodPerHour']
              lockey = 'DisplayNameLocKey' if amount == 1 else 'PluralDisplayNameLocKey'
              label = _(good['GoodSpec'][lockey])
              line('li', f'{amount} {label} per hour', ('data-searchable', good['GoodSpec']['Id'].lower()), ('data-category', 'consumer'))

        radius = (
          building.get('RangedEffectBuildingSpec', {}).get('EffectRadius') or
          building.get('AreaNeedApplierSpec', {}).get('ApplicationRadius'))
        def RenderEffects(specs):
          for specs in dict_group_by_id(specs, 'NeedId').values():
            spec = list(specs)[0]
            if spec['NeedId'] is None:  # required for EffectSpecification --> EffectSpecificationPerHour rename
              logging.warning(f'Empty need in {building['Id']}')
              continue
            need = self.needs[spec['NeedId'].lower()]
            needgroup = self.needgroups[need['NeedSpec']['NeedGroupId'].lower()]
            points = spec['Points'] if 'Points' in spec else spec['PointsPerHour']
            label = f'{_(needgroup['NeedGroupSpec']['DisplayNameLocKey'])}: {_(need['NeedSpec']['DisplayNameLocKey'])}'
            if radius:
              label = f'{label} {_('Needs.InRange').format(radius)}'
            line('li', label, ('data-searchable', need['NeedSpec']['Id'].lower()), ('data-category', 'consumer' if float(points) < 0 else 'producer'), klass='bad' if float(points) < 0 else 'good')

        with self.tag('ul', klass='needs'):
          RenderEffects(building.get('AreaNeedApplierSpec', {'Effects':[]})['Effects'])
          RenderEffects(building.get('DwellingSpec', {'SleepEffects':[]})['SleepEffects'])
          RenderEffects(building.get('WorkshopRandomNeedApplierSpec', {'Effects':[]})['Effects'])
          RenderEffects(building.get('AttractionSpec', {'Effects':[]})['Effects'])
          RenderEffects(building.get('ContinuousEffectBuildingSpec', {'Effects':[]})['Effects'])

        resources: dict[str, TemplateBlueprint] = {}
        with self.tag('table') as header:
          with header.tag('tr'):
            line('th', '', klass='name')
            plantable = building.get('PlanterBuildingSpec')
            if plantable:
              plants = self.plantable_by_group[plantable['PlantableResourceGroup'].lower()]
              for p in plants:
                resources[p['LabeledEntitySpec']['DisplayNameLocKey']] = p
              line('th', _(f'Pictogram.Plantable'))
            else:
              plants = None
            yieldable = building.get('YieldRemovingBuildingSpec')
            if yieldable:
              yield_type, yields = self.yieldable_by_group[yieldable['ResourceGroup'].lower()]
              for y in yields:
                yplantable = y.get('PlantableSpec')
                resources[y['LabeledEntitySpec']['DisplayNameLocKey']] = y
              line('th', _(f'Pictogram.{yield_type.removesuffix('Spec')}'))
            else:
              yield_type, yields = None, None

          for r in sorted(resources.items(), key=lambda r: r[1].get('NaturalResourceSpec', {}).get('Order', 0)):
            plant: TemplateBlueprint = r[1]
            searchable = [plant['Id'].lower()]
            categories = []
            if plants and plant in plants:
              categories.append('producer')
            for yt in ('CuttableSpec', 'GatherableSpec', 'RuinSpec'):
              if yt in plant:
                item = plant[yt]['YielderSpec']['Yield']['Id'].lower()
                if item != 'log' and item not in searchable:
                  searchable.append(item)
            if yields and plant in yields:
              categories.append('consumer')
            with self.tag('tr', ('data-searchable', ' '.join(searchable)), ('data-category', ' '.join(categories))):
              line('td', _(plant['LabeledEntitySpec']['DisplayNameLocKey']), klass='name')
              if plants:
                if plant in plants:
                  line('td', _('Time.HoursShort').format(plant['PlantableSpec']['PlantTimeInHours']))
                else:
                  line('td', '')
              if yields:
                assert yield_type
                if plant in yields:
                  line('td', _('Time.HoursShort').format(plant[yield_type]['YielderSpec']['RemovalTimeInHours']))
                else:
                  line('td', '')

      super().RenderBuilding(building)

  def RenderRecipe(self, recipe: RecipeBlueprint):
    _ = self.gettext
    line = self.doc.line
    with self.tag('div', klass='recipe card'):
      name = _(recipe['RecipeSpec']['DisplayLocKey'])
      line('div', name, klass='name')
      with self.tag('div', klass='stats'):
        line('div', f'{_('Time.HoursShort').format(recipe['RecipeSpec']['CycleDurationInHours'])}', klass='duration')

      with self.tag('div', klass='content'):

        with self.tag('ul', klass='ingredients'):
          if recipe['RecipeSpec']['Fuel']:
            good = self.goods[recipe['RecipeSpec']['Fuel'].lower()]
            amount = round(1 / recipe['RecipeSpec']['CyclesFuelLasts'], 3)
            lockey = 'DisplayNameLocKey' if amount == 1 else 'PluralDisplayNameLocKey'
            line('li', f'{amount} {_(good['GoodSpec'][lockey])}', ('data-searchable', good['GoodSpec']['Id'].lower()), ('data-category', 'consumer'))

          for x in recipe['RecipeSpec']['Ingredients']:
            if x['Id'].lower() not in self.goods:  # required for ZauerKraut in Librarybooks
              logging.warning(f'Missing ingredient {x['Id']} in {recipe['RecipeSpec']['Id']}')
              continue
            good = self.goods[x['Id'].lower()]
            lockey = 'DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'
            label = _(good['GoodSpec'][lockey])
            line('li', f'{x['Amount']} {label}', ('data-searchable', good['GoodSpec']['Id'].lower()), ('data-category', 'consumer'))

        with self.tag('ul', klass='products'):
          for x in recipe['RecipeSpec']['Products']:
            if x['Id'].lower() not in self.goods:  # required for Planks in GiantLogToPlanks
              logging.warning(f'Missing product {x['Id']} in {recipe['RecipeSpec']['Id']}')
              continue
            good = self.goods[x['Id'].lower()]
            lockey = 'DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'
            label = _(good['GoodSpec'][lockey])
            # TODO: Consider adding output storage size (for WB Omni recipe small, medium, large storage)
            line('li', f'{x['Amount']} {label}', ('data-searchable', good['GoodSpec']['Id'].lower()), ('data-category', 'producer'))

          if recipe['RecipeSpec']['ProducedSciencePoints'] > 0:
            line('li', f'{recipe['RecipeSpec']['ProducedSciencePoints']} {_('Science.SciencePoints')}', ('data-searchable', 'science'))

      super().RenderRecipe(recipe)

  def Write(self, filename):
    self.doc = yattag.Doc()
    self.doc.asis('<!DOCTYPE html>')
    with self.doc.tag('html'):
      self.RenderFaction(self.faction, pathlib.Path(filename))
    with open(f'{filename}.html', 'w', encoding='utf-8') as f:
      print(yattag.indent(self.doc.getvalue()), file=f)
    self.index.AddItem(self.gettext, self.faction, self.gettext(self.faction['FactionSpec']['DisplayNameLocKey']), f'{filename}.html')


class TextGenerator(Generator):

  stack: list[list[str]]

  @contextlib.contextmanager
  def NewContext(self, *headers, forced=False):
    item = []
    self.stack.append(item)
    yield item
    assert self.stack.pop() == item
    if item or forced:
      for i, h in enumerate(headers):
        item.insert(i, h)
    self.stack[-1].extend(item)

  @property
  def prefix(self):
    return '  ' * (len(self.stack) - 1)

  def RenderFaction(self, faction: FactionBlueprint):
    _ = self.gettext
    name = _(faction['FactionSpec']['DisplayNameLocKey'])
    self.stack[0].extend([
      name,
      '-' * len(name),
    ])
    super().RenderFaction(faction)

  def RenderNaturalResources(self, resources: list[TemplateBlueprint]):
    _ = self.gettext
    with self.NewContext(f'{self.prefix}{_('MapEditor.Layers.NaturalResources')}:') as c:
      super().RenderNaturalResources(resources)

  def RenderNaturalResource(self, r: TemplateBlueprint):
    _ = self.gettext
    plantable = r.get('PlantableSpec')

    name = _(r['LabeledEntitySpec']['DisplayNameLocKey'])
    if r['FloodableNaturalResourceSpec']['MinWaterHeight'] > 0:
      name = f'{_(f'Pictogram.Aquatic')} {name}'
    stats = [
      f'{_('Time.DaysShort').format(r['GrowableSpec']['GrowthTimeInDays'])}{_(f'Pictogram.Grows')}',
      f'{_('Time.DaysShort').format(r['WateredNaturalResourceSpec']['DaysToDieDry'])}{_(f'Pictogram.Dehydrates')}',
      f'{_('Time.DaysShort').format(r['FloodableNaturalResourceSpec']['DaysToDie'])}{_(f'Pictogram.Drowns')}',
    ]
    if 'GatherableSpec' in r:
      stats.append(f'{_('Time.DaysShort').format(r['GatherableSpec']['YieldGrowthTimeInDays'])}{_(f'Pictogram.Matures')}')

    heading = f'{self.prefix}{name} [{' '.join(stats)}]'
    with self.NewContext(heading, forced=True) as c:
      super().RenderNaturalResource(r)

  def RenderToolGroup(self, toolgroup: BlockObjectToolGroupBlueprint):
    _ = self.gettext
    if toolgroup['BlockObjectToolGroupSpec'].get('Type') == 'PlantingModeToolGroup':
      super().RenderToolGroup(toolgroup)
      return
    with self.NewContext(f'{self.prefix}{_(toolgroup['BlockObjectToolGroupSpec']['NameLocKey'])}:') as c:
      super().RenderToolGroup(toolgroup)

  def RenderBuilding(self, building: TemplateBlueprint):
    _ = self.gettext
    text = _(building['LabeledEntitySpec']['DisplayNameLocKey']).replace('\n', ' ')
    stats = []
    if 'DwellingSpec' in building:
      stats.append(f'{building['DwellingSpec']['MaxBeavers']}{_(f'Pictogram.Dwellers')}')
    if 'WorkplaceSpec' in building:
      stats.append(f'{building['WorkplaceSpec']['MaxWorkers']}{_(f'Pictogram.Workers')}')
    if 'MechanicalNodeSpec' in building and building['MechanicalNodeSpec']['PowerInput'] > 0:
      stats.append(f'{building['MechanicalNodeSpec']['PowerInput']}{_(f'Pictogram.Power')}')
    if building['BuildingSpec']['ScienceCost'] > 0:
      science = building['BuildingSpec']['ScienceCost']
      if science >= 1000:
        science = f'{science / 1000:n}k'
      stats.append(f'{science}{_(f'Pictogram.Science')}')
    if stats:
      text += f' [{' '.join(stats)}]'
    heading = f'{self.prefix}{text}:'
    with self.NewContext(heading) as c:
      for cost in building['BuildingSpec']['BuildingCost']:
        good = self.goods[cost['Id'].lower()]
        lockey = 'DisplayNameLocKey' if cost['Amount'] == 1 else 'PluralDisplayNameLocKey'
        label = _(good['GoodSpec'][lockey])
        c.append(f'{self.prefix}▶ {cost['Amount']} {label}')

      if 'GoodConsumingBuildingSpec' in building:
        for x in building['GoodConsumingBuildingSpec']['ConsumedGoods']:
          good = self.goods[x['GoodId'].lower()]
          amount = x['GoodPerHour']
          lockey = 'DisplayNameLocKey' if amount == 1 else 'PluralDisplayNameLocKey'
          label = _(good['GoodSpec'][lockey])
          c.append(f'{self.prefix}▶ {amount} {label} per hour')

      radius = (
        building.get('RangedEffectBuildingSpec', {}).get('EffectRadius') or
        building.get('AreaNeedApplierSpec', {}).get('ApplicationRadius'))
      def RenderEffects(specs):
        for specs in dict_group_by_id(specs, 'NeedId').values():
          spec = list(specs)[0]
          if spec['NeedId'] is None:  # required for EffectSpecification --> EffectSpecificationPerHour rename
            continue
          need = self.needs[spec['NeedId'].lower()]
          needgroup = self.needgroups[need['NeedSpec']['NeedGroupId'].lower()]
          points = spec['Points'] if 'Points' in spec else spec['PointsPerHour']
          sign = '▼' if float(points) < 0 else '▲'
          label = f'{_(needgroup['NeedGroupSpec']['DisplayNameLocKey'])}: {_(need['NeedSpec']['DisplayNameLocKey'])}'
          if radius:
            label = f'{label} {_('Needs.InRange').format(radius)}'
          c.append(f'{self.prefix}{sign} {label}')

      area_need = building.get('AreaNeedApplierSpec')
      if area_need:
        RenderEffects(area_need['Effects'])
      RenderEffects(building.get('DwellingSpec', {'SleepEffects':[]})['SleepEffects'])
      RenderEffects(building.get('WorkshopRandomNeedApplierSpec', {'Effects':[]})['Effects'])
      RenderEffects(building.get('AttractionSpec', {'Effects':[]})['Effects'])
      RenderEffects(building.get('ContinuousEffectBuildingSpec', {'Effects':[]})['Effects'])

      resources: dict[str, TemplateBlueprint] = {}
      plantable = building.get('PlanterBuildingSpec')
      if plantable:
        plants = self.plantable_by_group[plantable['PlantableResourceGroup'].lower()]
        for p in plants:
          resources[p['LabeledEntitySpec']['DisplayNameLocKey']] = p
      else:
        plants = None
      yieldable = building.get('YieldRemovingBuildingSpec')
      if yieldable:
        yield_type, yields = self.yieldable_by_group[yieldable['ResourceGroup'].lower()]
        for y in yields:
          yplantable = y.get('PlantableSpec')
          resources[y['LabeledEntitySpec']['DisplayNameLocKey']] = y
      else:
        yield_type, yields = None, None

      for r in sorted(resources.items(), key=lambda r: r[1].get('NaturalResourceSpec', {}).get('Order', 0)):
        plant: TemplateBlueprint = r[1]
        text = _(plant['LabeledEntitySpec']['DisplayNameLocKey'])
        stats = []
        if plants:
          if plant in plants:
            stats.append(f'{_('Time.HoursShort').format(plant['PlantableSpec']['PlantTimeInHours'])}{_(f'Pictogram.Plantable')}')
        if yields:
          assert yield_type
          if plant in yields:
            stats.append(f'{_('Time.HoursShort').format(plant[yield_type]['YielderSpec']['RemovalTimeInHours'])}{_(f'Pictogram.{yield_type.removesuffix('Spec')}')}')
        if stats:
          text += f' [{' '.join(stats)}]'
        c.append(f'{self.prefix}{text}')

      super().RenderBuilding(building)

    if not c:
      with self.NewContext(heading[:-1], forced=True) as c:
        pass

  def RenderRecipe(self, recipe: RecipeBlueprint):
    _ = self.gettext
    with self.NewContext(f'{self.prefix}{_(recipe['RecipeSpec']['DisplayLocKey'])} [{_('Time.HoursShort').format(recipe['RecipeSpec']['CycleDurationInHours'])}]') as c:
      if recipe['RecipeSpec']['Fuel']:
        good = self.goods[recipe['RecipeSpec']['Fuel'].lower()]
        amount = round(1 / recipe['RecipeSpec']['CyclesFuelLasts'], 3)
        lockey = 'DisplayNameLocKey' if amount == 1 else 'PluralDisplayNameLocKey'
        c.append(f'{self.prefix}▶ {amount} {_(good['GoodSpec'][lockey])}')

      for x in recipe['RecipeSpec']['Ingredients']:
        if x['Id'].lower() not in self.goods:
          continue
        good = self.goods[x['Id'].lower()]
        lockey = 'DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'
        label = _(good['GoodSpec'][lockey])
        c.append(f'{self.prefix}▶ {x['Amount']} {label}')

      for x in recipe['RecipeSpec']['Products']:
        if x['Id'].lower() not in self.goods:
          continue
        good = self.goods[x['Id'].lower()]
        lockey = 'DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'
        label = _(good['GoodSpec'][lockey])
        c.append(f'{self.prefix}◀ {x['Amount']} {label}')

      if recipe['RecipeSpec']['ProducedSciencePoints'] > 0:
        c.append(f'{self.prefix}◀ {recipe['RecipeSpec']['ProducedSciencePoints']} {_('Science.SciencePoints')}')

      super().RenderRecipe(recipe)

  def Write(self, filename):
    self.stack = [[]]
    self.RenderFaction(self.faction)
    lines, = self.stack
    with open(f'{filename}.txt', 'w', encoding='utf-8') as f:
      for line in lines:
        print(line, file=f)
    self.index.AddItem(self.gettext, self.faction, '[txt]', f'{filename}.txt')


def expand_directories(directories: list[str]) -> list[pathlib.Path]:
  result: list[pathlib.Path] = []
  for directory in directories:
    pattern = pathlib.Path(os.path.expandvars(directory)).expanduser()
    for parent in pattern.parents:
      if parent.exists(): break
    for path in braceexpand.braceexpand(str(pattern.relative_to(parent)), escape=False):
      paths = list(parent.glob(path))
      assert len(paths) > 0, f'len(glob({parent.joinpath(path)})) > 0'
      for path in paths:
        result.append(pathlib.Path(path))
  return result


def get_directories_and_versions(
    data_directories: list[str],
    mod_directories: list[str],
) -> tuple[list[pathlib.Path], dict[str, dict[str, typing.Any]]]:
  game_directories = expand_directories(data_directories)
  assert len(game_directories) == 1, f'Multiple game directories: {game_directories}'
  version_list = load_versions(game_directories, 'StreamingAssets/VersionNumbers.json')
  game_version = tuple(int(n) for n in version_list[0]['CurrentVersion'].split('.'))

  mod_version_directories: list[pathlib.Path] = []
  for directory in expand_directories(mod_directories):
    mod_version_paths = list(pathlib.Path(directory).glob('version-*', case_sensitive=False))
    if len(mod_version_paths) > 0:
      mod_versions = []
      for path in mod_version_paths:
        version = tuple(int(n) for n in path.name.removeprefix('version-').split('.'))
        if game_version >= version:
          mod_versions.append(version)
      mod_version = sorted(mod_versions, reverse=True)[0]
      directory = directory.joinpath('version-' + '.'.join(str(n) for n in mod_version)) 
    mod_version_directories.append(directory)

  version_list.extend(load_versions(mod_version_directories, 'manifest.json'))
  versions = {s.get('Id', 'timberborn').lower(): s for s in version_list}

  return game_directories + mod_version_directories, versions


def autoPath(path: str | os.PathLike) -> pathlib.Path | zipfile.Path:
  path = pathlib.Path(path)
  if path.suffix.lower() == '.zip' and path.exists():
    return zipfile.Path(path)
  else:
    return path


def add_backward_compatible_keys(d: dict):
  for blueprint in list(d.values()):
    for spec in blueprint.values():
      for _id in spec.get('BackwardCompatibleIds', []):
        if _id.lower() in d:
          logging.warning(f'Skipping backwards compatible {_id} for {spec['Id']}')
          continue
        assert _id.lower() not in d, _id
        logging.debug(f'Adding {_id} for {spec['Id']}')
        d[_id.lower()] = blueprint


def main():
  data_directories = [
    '%ProgramFiles(x86)%\\Steam\\steamapps\\common\\Timberborn\\Timberborn_Data',
    '~/Library/Application Support/Steam/steamapps/common/Timberborn/Timberborn.app/Contents/Resources/Data',
    '~/.steam/steam/steamapps/common/Timberborn/Timberborn_Data'
  ]
  data_directories = [
    dir for dir in data_directories if pathlib.Path(os.path.expandvars(dir)).expanduser().exists()
  ]
  mod_directories = []

  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument('-d', '--data', help='path to Timberborn Data directory', action='append', dest='data_directories', default=data_directories, metavar='PATH')
  parser.add_argument('-m', '--mods', help='path to Timberborn Mods directory', action='append', dest='mod_directories', default=mod_directories, metavar='PATH')
  parser.add_argument('-o', '--output', help='output path', default='out', metavar='PATH')
  language_arg = parser.add_argument('-l', '--language')
  parser.add_argument('-g', '--graph_grouping_threshold', help='threshold to split buildings with too-many recipes', type=int, default=5)
  parser.add_argument('-q', '--quiet', help='quiet mode (less messages)', action='store_true')
  parser.add_argument('-v', '--verbose', help='verbose mode (more messages)', action='store_true')
  parser.add_argument('-D', '--debug', help='debug mode (ignore cache, single threaded)', action='store_true')
  parser.add_argument('-S', '--src_link', help='link scripts and styles (insead of embedding them)', action='store_true')
  hparser = argparse.ArgumentParser(parents=[parser], add_help=False)
  hparser.add_argument('-h', '--help', action='store_true')
  args = hparser.parse_args()

  logging.basicConfig(
    level=logging.DEBUG if args.verbose else logging.WARNING if args.quiet else logging.INFO,
    format='%(message)s',
    datefmt='[%X]',
    handlers=[rich.logging.RichHandler()],
  )

  if len(args.data_directories) > len(data_directories):
    args.data_directories = args.data_directories[len(data_directories):]
  if len(args.mod_directories) > len(mod_directories):
    args.mod_directories = args.mod_directories[len(mod_directories):]
  directories, versions = get_directories_and_versions(args.data_directories, args.mod_directories)

  languages = []
  for i, directory in enumerate(directories):
    pattern_dir = f'Localizations' if i else f'StreamingAssets/Modding/Localizations.zip'
    pattern_path = autoPath(pathlib.Path.joinpath(directory, pattern_dir))
    patterns = ['*.txt', '*.csv']
    paths: list[pathlib.Path] = []
    for pattern in patterns:
      paths.extend(pathlib.Path(str(p)) for p in pattern_path.glob(pattern))
    for p in paths:
      if p.match('*_*'):
        continue
      language = p.relative_to(directory).stem
      if language not in languages:
        languages.append(language)
  languages.sort(key=lambda x: (len(x), x))

  language_arg.help=f'localization language to use (valid options: {', '.join(['all'] + languages)})'
  parser = argparse.ArgumentParser(parents=[parser])
  args = parser.parse_args()

  if not languages:
    raise SystemExit('No languages found, make sure the data option points Timberborn Data directory')
  if args.language == 'all':
    args.languages = languages
  else:
    args.languages = [l.strip() for l in (args.language or '').split(',') if l.strip()] or ['enUS']
  for l in args.languages:
    if l not in languages:
      parser.error(f'argument -l/--language: invalid choice: {l!r} (choose from {', '.join(['all'] + languages)})')

  cached = False
  hash = hashlib.sha256(repr(versions).encode())
  digest_parts = list(itertools.batched(hash.digest(), 4))
  short_digest = ''.join(f'{functools.reduce(operator.xor, x):02x}' for x in digest_parts)
  cache_file = f'.cache.{short_digest}'
  try:
    with open(cache_file, 'rb') as f:
      logging.info(f'Loading {cache_file}')
      d = pickle.load(f)

      if d['versions'] == versions:
        factions: dict[str, FactionBlueprint] = d['factions']
        goods: dict[str, GoodBlueprint] = d['goods']
        needgroups: dict[str, NeedGroupBlueprint] = d['needgroups']
        needs: dict[str, NeedBlueprint] = d['needs']
        recipes: dict[str, RecipeBlueprint] = d['recipes']
        toolgroups: dict[str, BlockObjectToolGroupBlueprint] = d['toolgroups']
        tools: dict[str, dict[str, ToolBlueprint]] = d['tools']
        templates: dict[str, dict[str, TemplateBlueprint]] = d['templates']
        if factions and goods and needs and needgroups and recipes and toolgroups and tools and templates:
          cached = True
  except:
    logging.warning(f'Missing/corrupt: {cache_file}')

  if not cached or args.debug:
    factions = {b['FactionSpec']['Id'].lower(): b for b in sorted(load_blueprints(directories, FactionBlueprint), key=lambda f: f['FactionSpec']['Order'])}
    # TODO: Handle FactionSpec.BlueprintModifiers
    goods = {b['GoodSpec']['Id'].lower(): b for b in load_blueprints(directories, GoodBlueprint)}
    needgroups = {b['NeedGroupSpec']['Id'].lower(): b for b in load_blueprints(directories, NeedGroupBlueprint)}
    needs = {b['NeedSpec']['Id'].lower(): b for b in load_blueprints(directories, NeedBlueprint)}
    recipes = {b['RecipeSpec']['Id'].lower(): b for b in load_blueprints(directories, RecipeBlueprint)}
    toolgroups_by_id = {b['BlockObjectToolGroupSpec']['Id'].lower(): b for b in load_blueprints(directories, BlockObjectToolGroupBlueprint, upgrade_toolgroup_blueprints)}
    def ToolGroupKey(b: BlockObjectToolGroupBlueprint | None):
      if not b:
        return ()
      k = (b['BlockObjectToolGroupSpec'].get('Layout', 'Default'), b['BlockObjectToolGroupSpec']['Order'])
      groupIds = b.get('ParentToolGroupSpec', {}).get('ParentIds')
      if groupIds:
        assert len(groupIds) == 1
        k = ToolGroupKey(toolgroups_by_id[groupIds[0].lower()]) + k
      return k
    toolgroups = {tg['BlockObjectToolGroupSpec']['Id'].lower(): tg for tg in sorted(toolgroups_by_id.values(), key=lambda kg: ToolGroupKey(kg))}
    templates, tool_lists = load_templates_and_tools(directories, factions, args.debug)
    tools: dict[str, dict[str, ToolBlueprint]] = {}
    for key in tool_lists:
      tools[key] = {b['ToolSpec']['Id'].lower(): b for b in sorted(tool_lists[key], key=lambda t: (ToolGroupKey(toolgroups.get(t['ToolSpec']['GroupId'].lower())), t['ToolSpec']['Order']))}
    d = dict(
      versions=versions,
      factions=factions,
      goods=goods,
      needgroups=needgroups,
      needs=needs,
      recipes=recipes,
      toolgroups=toolgroups,
      tools=tools,
      templates=templates,
    )
    with open(cache_file + '.json', 'w', encoding='utf-8') as f:
      json5.dump(d, f, indent=2, quote_keys=True, trailing_commas=False)
    with open(cache_file, 'wb') as f:
      pickle.dump(d, f, protocol=pickle.HIGHEST_PROTOCOL)

  add_backward_compatible_keys(goods)
  add_backward_compatible_keys(needs)
  add_backward_compatible_keys(recipes)

  os.makedirs(args.output, exist_ok=True)
  index = Index(args)
  generators = (
    HtmlGenerator,
    TextGenerator,
    GraphGenerator,
  )
  for language in args.languages:
    _ = load_translations(directories, language)
    for faction in factions.values():
      if faction['FactionSpec']['NewGameFullAvatar'].endswith('NO'):
        logging.info(f'Skipping {faction['FactionSpec']['Id']} in {_('Settings.Language.Name')}: {_(faction['FactionSpec']['DisplayNameLocKey'])}')
        continue
      logging.info(f'Generating {faction['FactionSpec']['Id']} in {_('Settings.Language.Name')}: {_(faction['FactionSpec']['DisplayNameLocKey'])}')
      faction_tools = tools['common'] | tools[faction['FactionSpec']['Id'].lower()]
      faction_templates = templates['common'] | templates[faction['FactionSpec']['Id'].lower()]
      for cls in generators:
        gen = cls(args, index, _, faction, goods, needgroups, needs, recipes, toolgroups, faction_tools, faction_templates)
        gen.Write(f'{args.output}/{language}_{faction['FactionSpec']['Id']}')
  logging.info('Generating index')
  index.Write(f'{args.output}/index.html', list(versions.values()))

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    exit(1)
