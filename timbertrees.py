#!/usr/bin/python3

import argparse
import builtins
import concurrent.futures
import contextlib
import csv
import functools
import hashlib
import itertools
import json5
import logging
import operator
import pathlib
import pickle
import pydot
import re
import rich.logging
import rich.progress
import typing
import unityparser
import unityparser.constants
import yattag
import yaml


# More can be found at https://timberapi.com/specifications/schemas/
class Spec(typing.TypedDict):
  pass


class Blueprint(typing.TypedDict):
  pass


class PrefabGroupSpec(Spec):
  Id: str
  Paths: list[str]


class PrefabGroupBlueprint(Blueprint):
  PrefabGroupSpec: PrefabGroupSpec


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
  GoodId: str
  Amount: int


class RecipeSpec(Spec):
  Id: str
  DisplayLocKey: str
  CycleDurationInHours: int
  Ingredients: list[GoodAmount]
  Products: list[GoodAmount]
  Fuel: str
  ProducedSciencePoints: int
  CyclesFuelLasts: int


class RecipeBlueprint(Blueprint):
  RecipeSpec: RecipeSpec

# TimberAPI specific and documented at https://timberapi.com/tools/
class ToolSpec(Spec):
  Id: str
  GroupId: str
  Order: int
  NameLocKey: str
  DevMode: typing.NotRequired[bool]
  Hidden: typing.NotRequired[bool]


class ToolBlueprint(Blueprint):
  ToolSpec: ToolSpec


# TimberAPI enhanced and documented at https://timberapi.com/tool_groups/
class ToolGroupSpec(Spec):
  Id: str
  Layout: str
  Order: int
  NameLocKey: str
  # Added by TimberAPI
  Type: typing.NotRequired[str]
  GroupId: typing.NotRequired[str]
  DevMode: typing.NotRequired[bool]
  Hidden: typing.NotRequired[bool]


class ToolGroupBlueprint(Blueprint):
  ToolGroupSpec: ToolGroupSpec

class FactionSpec(Spec):
  Id: str
  Order: int
  DisplayNameLocKey: str
  NewGameFullAvatar: str
  PrefabGroups: list[str]


class FactionBlueprint(Blueprint):
  FactionSpec: FactionSpec


class ContinuousEffectSpec(Spec):
  NeedId: str
  PointsPerHour: float


class NeedApplierEffectPerHour(Spec):
  NeedId: str
  Points: float
  ProbabilityPerHour: float


class Metadata(typing.TypedDict):
  guid: str


class MonoReferece(typing.TypedDict):
  fileID: int
  guid: str
  type: int


class MonoBehaviour(unityparser.constants.UnityClass):
  m_Script: MonoReferece


class BaseComponent(typing.TypedDict):
  pass


class BuildingSpec(BaseComponent):
  BuildingCost: list[GoodAmountSpec]
  ScienceCost: int


class LabeledEntitySpec(BaseComponent):
  DisplayNameLocKey: str


class NaturalResourceSpec(BaseComponent):
  Order: int


class PlaceableBlockObjectSpec(BaseComponent):
  ToolGroupId: str
  ToolOrder: int
  DevModeTool: int


class AreaNeedApplierSpec(BaseComponent):
  ApplicationRadius: int
  EffectPerHour: NeedApplierEffectPerHour


class ContinuousEffectBuildingSpec(BaseComponent):
  Effects: list[ContinuousEffectSpec]


class RangedEffectBuildingSpec(BaseComponent):
  EffectRadius: int


class WorkshopRandomNeedApplierSpec(BaseComponent):
  Effects: list[NeedApplierEffectPerHour]


class GoodConsumingBuildingSpec(BaseComponent):
  Supply: str
  Capacity: int
  GoodPerHour: float


class DwellingSpec(BaseComponent):
  MaxBeavers: int
  SleepEffects: list[ContinuousEffectSpec]


class WorkplaceSpec(BaseComponent):
  MaxWorkers: int


class ManufactorySpec(BaseComponent):
  ProductionRecipeIds: list[str]


class MechanicalNodeSpec(BaseComponent):
  PowerInput: int
  PowerOutput: int


class PlanterBuildingSpec(BaseComponent):
  PlantableResourceGroup: str


class PlantableSpec(BaseComponent):
  ResourceGroup: str
  PlantTimeInHours: float


class YielderSpec(BaseComponent):
  Yield: GoodAmountSpec
  RemovalTimeInHours: float
  ResourceGroup: str


class CuttableSpec(BaseComponent):
  YielderSpec: YielderSpec


class GatherableSpec(BaseComponent):
  YieldGrowthTimeInDays: float
  YielderSpec: YielderSpec


class GrowableSpec(BaseComponent):
  GrowthTimeInDays: float


class RuinSpec(BaseComponent):
  YielderSpec: YielderSpec


class CropSpec(BaseComponent):
  pass


class YieldRemovingBuildingSpec(BaseComponent):
  ResourceGroup: str


class PrefabSpec(BaseComponent):
  PrefabName: str


class WateredNaturalResourceSpec(BaseComponent):
  DaysToDieDry: float


class FloodableNaturalResourceSpec(BaseComponent):
  MinWaterHeight: int
  MaxWaterHeight: int
  DaysToDie: float


class Prefab(typing.TypedDict):
  Id: str
  BuildingSpec: BuildingSpec
  PrefabSpec: PrefabSpec
  LabeledEntitySpec: LabeledEntitySpec
  NaturalResourceSpec: NaturalResourceSpec
  PlaceableBlockObjectSpec: PlaceableBlockObjectSpec
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
    path: pathlib.Path
    optional: bool
    specification: T


def track[T](
    description: str,
    sequence: typing.Iterable[T],
    **kwargs,
) -> typing.Iterable[T]:
  return rich.progress.track(sequence, '%-36s' % description, **kwargs)


def load_versions(args: argparse.Namespace) -> tuple[list[dict[str, typing.Any]], dict[str, str]]:
  versions: list[dict[str, typing.Any]] = []
  prefixes: dict[str, str] = {}
  for i, directory in enumerate(track('Loading versions', args.directories, transient=True)):
    pattern = '../../manifest.json' if i else 'Assets/StreamingAssets/VersionNumbers.json'
    logging.debug(f'Scanning {pathlib.Path(directory).joinpath(pattern).resolve()}:')
    paths = [p for p in pathlib.Path(directory).glob(pattern, case_sensitive=False)]
    assert len(paths) == 1, f'len({pathlib.Path(directory)!r}.glob({pattern})) == {len(paths)}: {paths}'
    with open(paths[0], 'rt', encoding='utf-8-sig') as f:
      try:
        doc = typing.cast(dict, json5.load(f))
      except Exception as e:
        e.add_note(f'in {paths[0]}')
        raise
    if not i:
      assert 'Id' not in doc, directory
      prefixes[''] = directory
    else:
      assert 'Id' in doc, directory
      prefixes[doc['Id']] = directory
    versions.append(doc)
  return versions, prefixes


def read_metadata_file(directory: str, p: pathlib.Path) -> tuple[str, Metadata]:
  logging.debug(f'Loading {p.relative_to(directory)}')
  with open(p, 'rt', encoding='utf-8-sig') as f:
    return p.relative_to(directory).stem, yaml.load(f, yaml.SafeLoader)


def load_metadata(args: argparse.Namespace) -> dict[str, tuple[str, Metadata]]:
  map = builtins.map if args.debug else concurrent.futures.ProcessPoolExecutor().map
  metadata: dict[str, tuple[str, Metadata]] = {}
  pattern = f'**/*.meta'
  all_paths = []
  for directory in args.directories:
    paths = list(pathlib.Path(directory).glob(pattern, case_sensitive=False))
    all_paths.extend((directory, path) for path in paths)
  for p, meta in track(f'Loading unity metadata', map(read_metadata_file, *zip(*all_paths)), total=len(all_paths)):
    metadata[meta['guid']] = (p, meta)
  return metadata


def load_manifests(prefixes: dict[str, str]) -> dict[str, str]:
  manifests: dict[str, str] = {}
  for i, prefix in enumerate(track('Loading asset manifests', prefixes)):
    directory = prefixes[prefix]
    if not i:
      manifests[''] = str(pathlib.Path(directory).joinpath('Assets/Resources'))
      continue
    pattern = '../../AssetBundles/*.manifest'
    logging.debug(f'Scanning {pathlib.Path(directory).joinpath(pattern).resolve()}:')
    paths = [p for p in pathlib.Path(directory).glob(pattern, case_sensitive=False)]
    if not len(paths):
      logging.warning(f'No asset manifests found in {pathlib.Path(directory).joinpath(directory, 'AssetBundles')}')
    # assert len(paths) > 0, f'len(glob({pattern})) == {len(paths)}: {paths}'
    assets: dict[str, str] = {}
    for p in paths:
      with open(p, 'rt', encoding='utf-8-sig') as f:
        doc = yaml.load(f, yaml.SafeLoader)
        if 'Assets' in doc:
          for asset in doc['Assets']:
            asset_path = pathlib.PurePosixPath(asset)
            mod_path = pathlib.PurePosixPath(*asset_path.parts[5:])
            asset_id = str(mod_path.parent.joinpath(mod_path.stem)).lower()
            assert asset_id not in manifests
            pattern = str(pathlib.PurePosixPath(*asset_path.parts[:5]))
            asset_paths = list(pathlib.Path(directory).glob(pattern, case_sensitive=False))
            assert len(asset_paths) == 1, f'len({pathlib.Path(directory)!r}.glob({pattern})) == {len(asset_paths)}: {asset_paths}'
            asset_path = asset_paths[0]
            assets[asset_id] = str(asset_path)
    manifests.update(assets)
  return manifests


def upgrade_toolgroup_blueprints(
    blueprints: dict[str, list[PartialBlueprint[ToolGroupBlueprint]]]
):
  for toolgroup_specs in blueprints.values():
    for _, _, doc in toolgroup_specs:
      if 'Order' in doc['ToolGroupSpec']:
        doc['ToolGroupSpec']['Order'] = int(doc['ToolGroupSpec']['Order'])
  toolgroups = [
    ToolGroupBlueprint(ToolGroupSpec=ToolGroupSpec(
      Id='Fields',
      Layout='Blue',
      Order=20,
      Type='PlantingModeToolGroup',
      NameLocKey='ToolGroups.FieldsPlanting',
    )),
    ToolGroupBlueprint(ToolGroupSpec=ToolGroupSpec(
      Id='Forestry',
      Layout='Blue',
      Order=30,
      Type='PlantingModeToolGroup',
      NameLocKey='ToolGroups.ForestryPlanting',
    )),
  ]
  for toolgroup in toolgroups:
    toolgroup_specs = blueprints.setdefault(toolgroup['ToolGroupSpec']['Id'].lower(), [])
    if any(not i.optional for i in toolgroup_specs):
      logging.warning(f'Duplicate {toolgroup['ToolGroupSpec']['Id']} ToolGroup')
      # continue
    assert not any(not i.optional for i in toolgroup_specs)
    toolgroup_specs.insert(0, PartialBlueprint(pathlib.Path('builtin'), False, toolgroup))


def upgrade_tool_blueprints(
    prefabs: dict[str, dict[str, Prefab]],
    blueprints: dict[str, list[PartialBlueprint[ToolBlueprint]]]
):
  for tool_specs in blueprints.values():
    for _, _, doc in tool_specs:
      if 'Order' in doc['ToolSpec']:
        doc['ToolSpec']['Order'] = int(doc['ToolSpec']['Order'])
  tools: list[ToolBlueprint] = []
  for lst in prefabs.values():
    for item in lst.values():
      if 'PlaceableBlockObjectSpec' in item:
        spec = item['PlaceableBlockObjectSpec']
        tool = ToolBlueprint(ToolSpec=ToolSpec(
          Id=item['Id'],  # item['Prefab']['PrefabName'],
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
          Id=item['Id'],  # item['Prefab']['PrefabName'],
          GroupId='Fields' if 'CropSpec' in item else 'Forestry',
          Order=spec['Order'],
          NameLocKey=item['LabeledEntitySpec']['DisplayNameLocKey'],
        )))
  for tool in tools:
    tool_specs = blueprints.setdefault(tool['ToolSpec']['Id'].lower(), [])
    if any(not i.optional for i in tool_specs):
      logging.warning(f'Duplicate {tool['ToolSpec']['Id']} Tool')
      if tool['ToolSpec'].get('DevMode', False):
        continue  # Allow DevPowerGenerator to be specified in the per-faction PrefabGroupSpecification
    assert not any(not i.optional for i in tool_specs), tool_specs
    tool_specs.insert(0, PartialBlueprint(pathlib.Path('builtin'), False, tool))


def load_blueprints[T: Blueprint](
    args: argparse.Namespace,
    cls: type[T],
    upgrade_specs: typing.Callable[[dict[str, list[PartialBlueprint[T]]]], None] | None = None,
) -> list[T]:

  all_paths = []
  for i, directory in enumerate(args.directories):
    blueprint = cls.__name__.removesuffix('Blueprint')
    pattern = f'../../Blueprints/**/{blueprint}.*' if i else f'Assets/Resources/blueprints/**/{blueprint}.*'
    logging.debug(f'Scanning {pathlib.Path(directory).joinpath(pattern).resolve()}:')
    paths = [p for p in pathlib.Path(directory).glob(pattern, case_sensitive=False) if not p.match('*.meta')]
    assert paths or i or upgrade_specs, pathlib.Path(directory).joinpath(pattern).resolve()
    all_paths.extend((i, path) for path in paths)

  all_specs: dict[str, list[PartialBlueprint[T]]] = {}
  for i, p in track(f'Loading {cls.__name__.lower().replace('blueprint', ' blueprints')}', all_paths, total=len(all_paths)):
    logging.debug(f'Loading {p.resolve()}')
    blueprint_name, _, name = p.stem.lower().partition('.')
    assert blueprint_name + 'blueprint' == cls.__name__.lower()
    optional = name.endswith('.optional')
    name = name.replace('.optional', '')
    with open(p, 'rt', encoding='utf-8-sig') as f:
      try:
        # json5 doesn't support raw newlines
        # Maybe monkey-patch json5.parser.Parser._dqchar__c2_/_sqchar__c2_ to remove the no-eol condition in the seq?
        doc = typing.cast(T, json5.load(f))
      except Exception as e:
        e.add_note(f'in {paths[0]}')
        raise
    all_specs.setdefault(name, []).append(PartialBlueprint(p, optional, doc))
  if upgrade_specs:
    upgrade_specs(all_specs)

  merged_specs: dict[str, T] = {}
  for name, l in all_specs.items():
    for p, optional, doc in sorted(l, key=lambda i: (i.optional)):
      if optional:
        if name not in merged_specs:
          logging.debug(f'Skipping optional {p.resolve()}')
          continue
        # assert name in merged_specs, name
      spec = merged_specs.setdefault(name, cls())
      for k, v in doc.items():
        k, _, m = k.partition('#')
        i = spec.get(k, None)
        if isinstance(i, list) and m:
          assert isinstance(v, list), f'{name}.{k}: {v}'
          if m == 'append':
            i.extend(v)
          elif m == 'remove':
            for x in v:
              assert x in i
              i.remove(x)
          else:
            assert False, f'Unsupported mode: {name}.{k}#{m}: {v}'
        else:
          spec[k] = v

  return [s for s in merged_specs.values()]


def resolve_properties[T](
    val: dict[str, typing.Any],
    game_object: int,
    entries_by_id: dict[int, unityparser.constants.UnityClass],
    metadata: dict[str, tuple[str, Metadata]],
):
  if isinstance(val, dict):
    r = type(val)()
    for k, v in val.items():
      if k.startswith('m_'):
        continue
      elif k.startswith('_'):
        if isinstance(v, dict):
          if 'guid' in v:  # external reference
            meta = metadata.get(v['guid'])
            assert meta, v['guid']
            del v['guid']
            v['filename'] = meta[0]
          elif 'fileID' in v and v['fileID'] != 0:  # local reference
            if v['fileID'] not in entries_by_id:
              logging.warning(f'Missing file {v['fileID']} for ref, skipping')
              r[k[1].upper() + k[2:]] = v
              continue
            entry = entries_by_id[v['fileID']]
            if entry.__class_name == 'GameObject' or entry.m_GameObject['fileID'] == game_object:  # type: ignore
              del entries_by_id[v['fileID']]  # remove to prevent top-level references
            v = type(v)(entry.get_serialized_properties_dict())
        v = resolve_properties(v, game_object, entries_by_id, metadata)
        r[k[1].upper() + k[2:]] = v
      else:
        r[k] = v
    return r
  elif isinstance(val, list):
    return type(val)(resolve_properties(x, game_object, entries_by_id, metadata) for x in typing.cast(list, val))
  return val


def load_prefab(
    manifests: dict[str, str],
    metadata: dict[str, tuple[str, Metadata]],
    file_path: str,
):
  if file_path.lower() in manifests:
    directory = manifests[file_path.lower()]
  else:
    directory = manifests['']
  pattern = f'{file_path}.prefab'

  paths = list(pathlib.Path(directory).glob(pattern, case_sensitive=False))
  assert len(paths) == 1, f'len({pathlib.Path(directory)!r}.glob({pattern})) == {len(paths)}: {paths}'
  logging.debug(f'Loading {paths[0].relative_to(directory)}')
  doc = unityparser.UnityDocument.load_yaml(paths[0])
  entries_by_id: dict[int, unityparser.constants.UnityClass] = {int(e.anchor): e for e in doc.entries}
  prefab: Prefab = typing.cast(Prefab, dict(Id=doc.entry.m_Name))

  for component in doc.entry.m_Component:
    entry = entries_by_id.pop(component['component']['fileID'], None)
    if not entry:  # already consumed
      continue
    if entry.__class_name != 'MonoBehaviour':
      continue
    behaviour = typing.cast(MonoBehaviour, entry)
    guid = behaviour.m_Script['guid']
    meta = metadata.get(guid)
    assert meta, f'Missing script {guid} for behaviour in {prefab['Id']}'
    if not meta:
      logging.warning(f'Missing script {guid} for behaviour in {prefab['Id']}, skipping')
      continue
    properties = behaviour.get_serialized_properties_dict()
    resolved_properties = resolve_properties(properties, int(doc.entry.anchor), entries_by_id, metadata)
    prefab[pathlib.Path(meta[0]).stem] = resolved_properties

  return prefab


def load_prefabs(
    args: argparse.Namespace,
    manifests: dict[str, str],
    metadata: dict[str, tuple[str, Metadata]],
    factions: dict[str, FactionBlueprint],
) -> dict[str, dict[str, Prefab]]:
  map = builtins.map if args.debug else concurrent.futures.ProcessPoolExecutor().map
  prefabs: dict[str, dict[str, Prefab]] = {'common': {}}

  prefabgroups = load_blueprints(args, PrefabGroupBlueprint)
  commonpaths = list(itertools.chain.from_iterable(
    typing.cast(list, b['PrefabGroupSpec']['Paths']) for b in prefabgroups if b['PrefabGroupSpec']['Id'].lower() == 'common'))

  for prefab in track(f'Loading common prefabs', map(load_prefab, *zip(*((manifests, metadata, prefab) for prefab in commonpaths))), total=len(commonpaths)):
    assert prefab and prefab['Id'].lower() not in prefabs['common']
    prefabs['common'][prefab['Id'].lower()] = prefab

  for key, faction in factions.items():
    if faction['FactionSpec']['NewGameFullAvatar'].endswith('NO'):
      logging.warning(f'Skipping {faction['FactionSpec']['Id']} because avatar ends with NO')
      continue

    faction_groups = tuple(g.lower() for g in faction['FactionSpec']['PrefabGroups'])
    faction_prefabs = list(itertools.chain.from_iterable(
      typing.cast(list, b['PrefabGroupSpec']['Paths']) for b in prefabgroups if b['PrefabGroupSpec']['Id'].lower() in faction_groups))
    prefabs[key] = {}
    for prefab in track(f'Loading {faction['FactionSpec']['Id']} prefabs', map(load_prefab, *zip(*((manifests, metadata, prefab) for prefab in faction_prefabs))), total=len(faction_prefabs)):
      assert prefab
      assert prefab['Id'].lower() not in prefabs[key], prefab['Id']
      if prefab['Id'].lower() in prefabs[key]:
        breakpoint()
      prefabs[key][prefab['Id'].lower()] = prefab
  return prefabs


def load_translations(args: argparse.Namespace, language: str):
  csv.register_dialect('timberborn', skipinitialspace=True, strict=True)
  catalog: dict[str, str] = {}
  for i, directory in enumerate(args.directories):
    pattern_dir = f'../../Localizations/' if i else f'Assets/Resources/localizations/'
    patterns = [f'{pattern_dir}{language}{suffix}' for suffix in ['*.txt', '*.csv']]
    paths = []
    for pattern in patterns:
      paths.extend(pathlib.Path(directory).glob(pattern, case_sensitive=False))
    # assert len(paths) <= 1, f'len(glob({pattern})) == {len(paths)}: {paths}'
    for x in paths:
      with open(x, 'rt', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, dialect='timberborn')
        try:
          for row in reader:
            if not i and row['ID'] in catalog:
              logging.warning(f'Duplicate key {row['ID']!r} on line {reader.line_num} of {x.resolve()}')
              # For duplicate key in WB en_US
              assert row['ID'] not in catalog, f'Duplicate key {row['ID']!r} on line {reader.line_num} of {x.resolve()}'
            catalog[row['ID']] = row['Text']
        except Exception as e:
          e.add_note(f'Loading {x.resolve()} on line {reader.line_num}')
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

  def gettext(message: str):
    if message in catalog:
      return catalog[message]
    if message.endswith('DisplayName'):
      suffix = 's' if message.endswith('PluralDisplayName') else ''
      guess = message.rpartition('.')[0].rpartition('.')[2]
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
    if group is not None:  # required for EffectSpecification --> EffectSpecificationPerHour rename
      group = typing.cast(str, group).lower()
    else:
      logging.warning(f'Missing key in dict_group_by_id: {key}')
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

  def Write(self, filename):
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
          with doc.tag('script', src='../script.js'):
            pass
        else:
          with doc.tag('style'):
            with open('style.css', 'rt', encoding='utf-8-sig') as f:
              doc.asis('\n' + f.read())
          with doc.tag('script'):
            with open('script.js', 'rt', encoding='utf-8-sig') as f:
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
    with open(filename, 'wt', encoding='utf-8') as f:
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
      toolgroups: dict[str, ToolGroupBlueprint],
      tools: dict[str, ToolBlueprint],
      all_prefabs: dict[str, dict[str, Prefab]],
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
    self.toolgroups_by_group = dict_group_by_id(toolgroups.values(), 'ToolGroupSpec.GroupId')
    self.tools_by_group = dict_group_by_id(tools.values(), 'ToolSpec.GroupId')
    prefabs = list(all_prefabs['common'].values()) + list(all_prefabs[faction['FactionSpec']['Id'].lower()].values())
    self.prefabs = {prefab['Id'].lower(): prefab for prefab in prefabs if 'PrefabSpec' in prefab}
    self.natural_resources: list[Prefab] = sorted(
      [p for p in prefabs if 'NaturalResourceSpec' in p],
      key=lambda p: ('CropSpec' not in p, p['NaturalResourceSpec']['Order'])
    )
    self.plantable_by_group = dict_group_by_id(prefabs, 'PlantableSpec.ResourceGroup')
    self.planter_building_by_group = dict_group_by_id(prefabs, 'PlanterBuildingSpec.PlantableResourceGroup')
    cuttable_by_group = dict_group_by_id(prefabs, 'CuttableSpec.YielderSpec.ResourceGroup')
    gatherable_by_group = dict_group_by_id(prefabs, 'GatherableSpec.YielderSpec.ResourceGroup')
    scavengable_by_group = dict_group_by_id(prefabs, 'RuinSpec.YielderSpec.ResourceGroup')
    self.yieldable_by_group: dict[
      str,
      tuple[typing.Literal['CuttableSpec'], list[Prefab]] |
      tuple[typing.Literal['GatherableSpec'], list[Prefab]] |
      tuple[typing.Literal['RuinSpec'], list[Prefab]]
    ] = {}
    self.yieldable_by_group.update({k: ('CuttableSpec', v) for k, v in cuttable_by_group.items()})
    self.yieldable_by_group.update({k: ('GatherableSpec', v) for k, v in gatherable_by_group.items()})
    self.yieldable_by_group.update({k: ('RuinSpec', v) for k, v in scavengable_by_group.items()})

  def IsPlantableResourceGroupVisible(self, group: str) -> bool:
    def IsToolGroupHidden(prefab: Prefab) -> bool:
      name = prefab['PlaceableBlockObjectSpec']['ToolGroupId']
      tg = self.toolgroups.get(name.lower())
      if not tg:
        return True
      return bool(tg.get('Hidden'))
    return not all(IsToolGroupHidden(x) for x in self.planter_building_by_group[group.lower()])

  def RenderFaction(self, faction: FactionBlueprint):
    self.RenderNaturalResources(self.natural_resources)
    for b in self.toolgroups_by_group['']:
      if b['ToolGroupSpec'].get('Type') != 'PlantingModeToolGroup':
        self.RenderToolGroup(b)

  def RenderNaturalResources(self, resources: list[Prefab]):
    for b in self.toolgroups_by_group['']:
      if b['ToolGroupSpec'].get('Type') == 'PlantingModeToolGroup':
        self.RenderToolGroup(b)

  def RenderToolGroup(self, toolgroup: ToolGroupBlueprint):
    if toolgroup['ToolGroupSpec'].get('DevMode'):
      logging.debug(f'Skipping DevMode ToolGroup {toolgroup['ToolGroupSpec']['Id']}')
      return
    if toolgroup['ToolGroupSpec'].get('Hidden'):
      logging.debug(f'Skipping Hidden ToolGroup {toolgroup['ToolGroupSpec']['Id']}')
      return
    items: list[tuple[int, typing.Literal[True], ToolGroupBlueprint] | tuple[int, typing.Literal[False], ToolBlueprint]] = []
    for tool in self.tools_by_group.get(toolgroup['ToolGroupSpec']['Id'].lower(), []):
      items.append((tool['ToolSpec']['Order'], False, tool))
    for tg in self.toolgroups_by_group.get(toolgroup['ToolGroupSpec']['Id'].lower(), []):
      items.append((tg['ToolGroupSpec']['Order'], True, tg))

    for _, is_group, item in sorted(items, key=lambda x: (x[0], x[1])):
      if is_group:
        toolgroup = typing.cast(ToolGroupBlueprint, item)
        self.RenderToolGroup(toolgroup)
      else:
        tool = typing.cast(ToolBlueprint, item)
        if tool['ToolSpec'].get('DevMode'):
          logging.debug(f'Skipping DevMode Tool {tool['ToolSpec']['Id']}')
          continue
        if tool['ToolSpec'].get('Hidden'):
          logging.debug(f'Skipping Hidden Tool {tool['ToolSpec']['Id']}')
          continue
        prefab = self.prefabs.get(tool['ToolSpec']['Id'].lower())
        if not prefab:  # TODO: Come up with a better way to do per-faction tools
          logging.debug(f'Skipping prefab for {tool['ToolSpec']['Id']}')
          continue
        if 'PlantableSpec' in prefab:
          self.RenderNaturalResource(prefab)
        if 'PlaceableBlockObjectSpec' in prefab:
          if 'BuildingSpec' not in prefab: return  # FIXME
          self.RenderBuilding(prefab)

  def RenderBuilding(self, building: Prefab):
    for r in building.get('ManufactorySpec', {}).get('ProductionRecipeIds', []):
      if r.lower() not in self.recipes:
        logging.warning(f'Skipping missing recipe: {r}')
        continue
      self.RenderRecipe(self.recipes[r.lower()])

  def RenderNaturalResource(self, resource: Prefab): ...
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

  def RenderFaction(self, faction: FactionBlueprint, prefabs: typing.Collection[Prefab], toolgroups: dict[str, ToolGroupBlueprint] ):
    _ = self.dottext

    self.graph.set_name(faction['FactionSpec']['Id'])
    self.graph.set_label(_(faction['FactionSpec']['DisplayNameLocKey']))  # type: ignore
    self.graph.add_node(pydot.Node(
      'SciencePoints',
      label=_('Science.SciencePoints'),
      # image='sprites/bottombar/buildinggroups/Science.png',
    ))

    for building in prefabs:
      if building.get('PlaceableBlockObjectSpec', {}).get('ToolGroupId', '').lower() not in toolgroups:
        continue
      toolgroup = toolgroups[building['PlaceableBlockObjectSpec']['ToolGroupId'].lower()]
      if toolgroup['ToolGroupSpec'].get('Hidden'):
        continue

      building_goods = set()
      for c in building.get('Building', {}).get('BuildingCost', []):
        building_goods.add(c['GoodId'])

      recipes = building.get('ManufactorySpec', {}).get('ProductionRecipeIds', [])
      for r in recipes:
        sg = pydot.Subgraph(
          building['Id'] + ('.' + r if len(recipes) > self.args.graph_grouping_threshold else ''),
          cluster=True,
          label=f'[{_(toolgroup['ToolGroupSpec']['NameLocKey'])}]\n{_(building['LabeledEntitySpec']['DisplayNameLocKey'])}',
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
        style='dashed' if good['GoodSpec']['Id'] in building_goods else 'solid',
        color='#b30000',
      ))

    for x in recipe['RecipeSpec']['Ingredients']:
      if x['Id'].lower() not in self.goods:
        continue
      good = self.goods[x['Id'].lower()]
      #if good['Id'] in building_goods:
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
        style='dashed' if good['GoodSpec']['Id'] in building_goods else 'solid',
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
      # imagepath=args.directories[0],
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

    self.RenderFaction(self.faction, self.prefabs.values(), self.toolgroups)

    self.graph.write(f'{filename}.dot', format='raw')
    self.graph.write(f'{filename}.svg', format='svg')

    self.index.AddItem(self.gettext, self.faction, '[svg]', f'{filename}.svg')


class HtmlGenerator(Generator):

  style: str = ''
  script: str = ''

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if not self.style:
      logging.debug('Loading style.css')
      with open('style.css', 'rt', encoding='utf-8-sig') as f:
        type(self).style = f.read()
    if not self.script:
      logging.debug('Loading script.js')
      with open('script.js', 'rt', encoding='utf-8-sig') as f:
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

  def RenderNaturalResources(self, resources: list[Prefab]):
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

  def RenderNaturalResource(self, r: Prefab):
    _ = self.gettext
    line = self.doc.line
    plantable = r.get('PlantableSpec')
    if not self.IsPlantableResourceGroupVisible(plantable['ResourceGroup']):
      return
    searchable = [r['Id'].lower()]
    for yield_type in ('CuttableSpec', 'GatherableSpec', 'RuinSpec'):
      if yield_type in r:
        item = r[yield_type]['YielderSpec']['Yield']['GoodId'].lower()
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

  def RenderToolGroup(self, toolgroup: ToolGroupBlueprint):
    _ = self.gettext
    line = self.doc.line
    if toolgroup['ToolGroupSpec'].get('Type') == 'PlantingModeToolGroup':
      super().RenderToolGroup(toolgroup)
      return
    with self.tag('div', klass='toolgroup card') as header:
      header.line('div', _(toolgroup['ToolGroupSpec']['NameLocKey']), klass='name')
      super().RenderToolGroup(toolgroup)

  def RenderBuilding(self, building: Prefab):
    _ = self.gettext
    line = self.doc.line
    with self.tag('div', klass='building card') as header:
      name = _(building['LabeledEntitySpec']['DisplayNameLocKey']).replace('\n', ' ')
      header.line('div', name, klass='name')
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
            good = self.goods[x['GoodId'].lower()]
            amount = x['Amount']
            lockey = 'DisplayNameLocKey' if amount == 1 else 'PluralDisplayNameLocKey'
            label = _(good['GoodSpec'][lockey])
            line('li', f'{amount} {label}', ('data-searchable', good['GoodSpec']['Id'].lower()), ('data-category', 'consumer'))

          if 'GoodConsumingBuildingSpec' in building:
            good = self.goods[building['GoodConsumingBuildingSpec']['Supply'].lower()]
            amount = building['GoodConsumingBuildingSpec']['GoodPerHour']
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
          area_need = building.get('AreaNeedApplierSpec')
          if area_need:
            RenderEffects([area_need['EffectPerHour']])
          RenderEffects(building.get('DwellingSpec', {'SleepEffects':[]})['SleepEffects'])
          RenderEffects(building.get('WorkshopRandomNeedApplierSpec', {'Effects':[]})['Effects'])
          RenderEffects(building.get('AttractionSpec', {'Effects':[]})['Effects'])
          RenderEffects(building.get('ContinuousEffectBuildingSpec', {'Effects':[]})['Effects'])

        resources: dict[str, Prefab] = {}
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
                if yplantable and not self.IsPlantableResourceGroupVisible(yplantable['ResourceGroup']):
                  continue
                resources[y['LabeledEntitySpec']['DisplayNameLocKey']] = y
              line('th', _(f'Pictogram.{yield_type.removesuffix('Spec')}'))
            else:
              yield_type, yields = None, None

          for r in sorted(resources.items(), key=lambda r: r[1].get('NaturalResourceSpec', {}).get('Order', 0)):
            plant: Prefab = r[1]
            searchable = [plant['Id'].lower()]
            categories = []
            if plants and plant in plants:
              categories.append('producer')
            for yt in ('CuttableSpec', 'GatherableSpec', 'RuinSpec'):
              if yt in plant:
                item = plant[yt]['YielderSpec']['Yield']['GoodId'].lower()
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
    with open(f'{filename}.html', 'wt', encoding='utf-8') as f:
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

  def RenderNaturalResources(self, resources: list[Prefab]):
    _ = self.gettext
    with self.NewContext(f'{self.prefix}{_('MapEditor.Layers.NaturalResources')}:') as c:
      super().RenderNaturalResources(resources)

  def RenderNaturalResource(self, r: Prefab):
    _ = self.gettext
    plantable = r.get('PlantableSpec')
    if not self.IsPlantableResourceGroupVisible(plantable['ResourceGroup']):
      return

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

  def RenderToolGroup(self, toolgroup: ToolGroupBlueprint):
    _ = self.gettext
    if toolgroup['ToolGroupSpec'].get('Type') == 'PlantingModeToolGroup':
      super().RenderToolGroup(toolgroup)
      return
    with self.NewContext(f'{self.prefix}{_(toolgroup['ToolGroupSpec']['NameLocKey'])}:') as c:
      super().RenderToolGroup(toolgroup)

  def RenderBuilding(self, building: Prefab):
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
        good = self.goods[cost['GoodId'].lower()]
        lockey = 'DisplayNameLocKey' if cost['Amount'] == 1 else 'PluralDisplayNameLocKey'
        label = _(good['GoodSpec'][lockey])
        c.append(f'{self.prefix}▶ {cost['Amount']} {label}')

      if 'GoodConsumingBuildingSpec' in building:
        good = self.goods[building['GoodConsumingBuildingSpec']['Supply'].lower()]
        amount = building['GoodConsumingBuildingSpec']['GoodPerHour']
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
        RenderEffects([area_need['EffectPerHour']])
      RenderEffects(building.get('DwellingSpec', {'SleepEffects':[]})['SleepEffects'])
      RenderEffects(building.get('WorkshopRandomNeedApplierSpec', {'Effects':[]})['Effects'])
      RenderEffects(building.get('AttractionSpec', {'Effects':[]})['Effects'])
      RenderEffects(building.get('ContinuousEffectBuildingSpec', {'Effects':[]})['Effects'])

      resources: dict[str, Prefab] = {}
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
          if yplantable and not self.IsPlantableResourceGroupVisible(yplantable['ResourceGroup']):
            continue
          resources[y['LabeledEntitySpec']['DisplayNameLocKey']] = y
      else:
        yield_type, yields = None, None

      for r in sorted(resources.items(), key=lambda r: r[1].get('NaturalResourceSpec', {}).get('Order', 0)):
        plant: Prefab = r[1]
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

    if not c and stats:
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
    with open(f'{filename}.txt', 'wt', encoding='utf-8') as f:
      for line in lines:
        print(line, file=f)
    self.index.AddItem(self.gettext, self.faction, '[txt]', f'{filename}.txt')


def main():
  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument('-d', '--directory', help='full path to ExportedProject(s)', action='append', dest='directories', default=[], required=True)
  language_arg = parser.add_argument('-l', '--language')
  parser.add_argument('-g', '--graph_grouping_threshold', help='threshold to split buildings with too-many recipes', type=int, default=5)
  parser.add_argument('-q', '--quiet', help='quiet mode (less messages)', action='store_true')
  parser.add_argument('-v', '--verbose', help='verbose mode (more messages)', action='store_true')
  parser.add_argument('-D', '--debug', help='debug mode (ignore cache, single threaded)', action='store_true')
  parser.add_argument('-S', '--src_link', help='link scripts and styles (insead of embedding them)', action='store_true')
  hparser = argparse.ArgumentParser(parents=[parser], add_help=False)
  hparser.add_argument('-h', '--help', action='store_true')
  args = hparser.parse_args()

  languages = []
  for directory in args.directories:
    pattern = f'Assets/Resources/localizations/*.txt'
    for p in list(pathlib.Path(directory).glob(pattern, case_sensitive=False)):
      if p.match('*_*') or p.match('reference*'):
        continue
      language = p.relative_to(directory).stem
      if language not in languages:
        languages.append(language)
    languages.sort(key=lambda x: (len(x), x))
  if not languages:
    raise SystemExit('No languages found, make sure the directory option points to an ExportedProject')

  language_arg.help=f'localization language to use (valid options: {', '.join(['all'] + languages)})'
  parser = argparse.ArgumentParser(parents=[parser])
  args = parser.parse_args()

  if args.language == 'all':
    args.languages = languages
  else:
    args.languages = [l.strip() for l in (args.language or '').split(',') if l.strip()] or ['enUS']
  for l in args.languages:
    if l not in languages:
      parser.error(f'argument -l/--language: invalid choice: {l!r} (choose from {', '.join(['all'] + languages)})')

  logging.basicConfig(
    level=logging.DEBUG if args.verbose else logging.WARNING if args.quiet else logging.INFO,
    format='%(message)s',
    datefmt='[%X]',
    handlers=[rich.logging.RichHandler()],
  )

  version_list, prefixes = load_versions(args)
  versions = {s.get('Id', 'timberborn').lower(): s for s in version_list}

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
        toolgroups: dict[str, ToolGroupBlueprint] = d['toolgroups']
        tools: dict[str, ToolBlueprint] = d['tools']
        prefabs: dict[str, dict[str, Prefab]] = d['prefabs']
        if factions and goods and needs and needgroups and recipes and toolgroups and tools and prefabs:
          cached = True
  except:
    logging.warning(f'Missing/corrupt: {cache_file}')

  if not cached or args.debug:
    factions = {b['FactionSpec']['Id'].lower(): b for b in sorted(load_blueprints(args, FactionBlueprint), key=lambda f: f['FactionSpec']['Order'])}
    goods = {b['GoodSpec']['Id'].lower(): b for b in load_blueprints(args, GoodBlueprint)}
    needgroups = {b['NeedGroupSpec']['Id'].lower(): b for b in load_blueprints(args, NeedGroupBlueprint)}
    needs = {b['NeedSpec']['Id'].lower(): b for b in load_blueprints(args, NeedBlueprint)}
    recipes = {b['RecipeSpec']['Id'].lower(): b for b in load_blueprints(args, RecipeBlueprint)}
    toolgroups_by_id = {b['ToolGroupSpec']['Id'].lower(): b for b in load_blueprints(args, ToolGroupBlueprint, upgrade_toolgroup_blueprints)}
    def ToolGroupKey(b: ToolGroupBlueprint | None):
      if not b:
        return ()
      k = (b['ToolGroupSpec'].get('Layout', 'Default'), b['ToolGroupSpec']['Order'])
      groupId = b['ToolGroupSpec'].get('GroupId')
      if groupId:
        k = ToolGroupKey(toolgroups_by_id[groupId.lower()]) + k
      return k
    toolgroups = {tg['ToolGroupSpec']['Id'].lower(): tg for tg in sorted(toolgroups_by_id.values(), key=lambda kg: ToolGroupKey(kg))}
    manifests = load_manifests(prefixes)
    metadata = load_metadata(args)
    prefabs = load_prefabs(args, manifests, metadata, factions)
    tools = {b['ToolSpec']['Id'].lower(): b for b in load_blueprints(args, ToolBlueprint, functools.partial(upgrade_tool_blueprints, prefabs))}
    tools = {b['ToolSpec']['Id'].lower(): b for b in sorted(tools.values(), key=lambda t: (ToolGroupKey(toolgroups.get(t['ToolSpec']['GroupId'].lower())), t['ToolSpec']['Order']))}
    d = dict(
      versions=versions,
      factions=factions,
      goods=goods,
      needgroups=needgroups,
      needs=needs,
      recipes=recipes,
      toolgroups=toolgroups,
      tools=tools,
      prefabs=prefabs,
    )
    with open(cache_file + '.json', 'wt', encoding='utf-8') as f:
      json5.dump(d, f, indent=2, quote_keys=True, trailing_commas=False)
    with open(cache_file, 'wb') as f:
      pickle.dump(d, f, protocol=pickle.HIGHEST_PROTOCOL)

  index = Index(args)
  generators = (
    HtmlGenerator,
    TextGenerator,
    GraphGenerator,
  )
  for language in args.languages:
    _ = load_translations(args, language)
    for faction in factions.values():
      if faction['FactionSpec']['NewGameFullAvatar'].endswith('NO'):
        logging.info(f'Skipping {faction['FactionSpec']['Id']} in {_('Settings.Language.Name')}: {_(faction['FactionSpec']['DisplayNameLocKey'])}')
        continue
      logging.info(f'Generating {faction['FactionSpec']['Id']} in {_('Settings.Language.Name')}: {_(faction['FactionSpec']['DisplayNameLocKey'])}')
      for cls in generators:
        gen = cls(args, index, _, faction, goods, needgroups, needs, recipes, toolgroups, tools, prefabs)
        gen.Write(f'out/{language}_{faction['FactionSpec']['Id']}')
  index.Write('out/index.html')

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    exit(1)
