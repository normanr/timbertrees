#!/usr/bin/python3

import argparse
import builtins
import concurrent.futures
import contextlib
import csv
import hashlib
import itertools
import json5
import pathlib
import pickle
import pydot
import re
import typing
import unityparser
import unityparser.constants
import yattag
import yaml


def load_specifications(args, type):
  files = {}
  pattern = f'Resources/specifications/**/{type}Specification.*'
  for i, directory in enumerate(args.directories):
    found = False
    print(f'Scanning {pathlib.Path(directory).joinpath(pattern)}:')
    for p in pathlib.Path(directory).glob(pattern, case_sensitive=False):
      if p.match('*.meta'):
        continue
      print(f'Loading {p.relative_to(directory)}')
      s = p.stem.lower().removeprefix(f'{type.lower()}specification.')
      if not i or s.endswith('.original'):
        s = s.removesuffix('.original')
        assert s not in files
      if s.endswith('.replace'):
        s = s.removesuffix('.replace')
        del files[s]
      with open(p, 'rt', encoding='utf-8-sig') as f:
        doc = typing.cast(dict[str, str | int | list[str]], json5.load(f))
      spec = files.setdefault(s, {})
      for k, v in doc.items():
        if isinstance(spec.get(k, None), list):
          spec[k].extend(v)
        else:
          spec[k] = v
      found = True
    assert found or i, directory
  return [s for s in files.values()]


def read_metadata_file(directory, p):
  print(f'Loading {p.relative_to(directory)}')
  with open(p, 'rt', encoding='utf-8-sig') as f:
    return yaml.load(f, yaml.SafeLoader)['guid'], pathlib.Path(p.stem).stem


def load_metadata(args, type) -> dict[str, str]:
  map = builtins.map if args.debug else concurrent.futures.ProcessPoolExecutor().map
  metadata = {}
  pattern = f'{type}.meta'
  for directory in args.directories:
    paths = list(pathlib.Path(directory).glob(pattern, case_sensitive=False))
    for k, v in map(read_metadata_file, *zip(*((directory, p) for p in paths))):
      metadata[k] = v
  return metadata


def resolve_properties[T](val: T, game_object: int, entries_by_id: dict[int, unityparser.constants.UnityClass]) -> T:
  if isinstance(val, dict):
    r = type(val)()
    for k, v in val.items():
      if k.startswith('m_'):
        continue
      elif k.startswith('_'):
        if isinstance(v, dict):
          if 'guid' in v:  # reference to an external file?
            continue
          if 'fileID' in v and v['fileID'] != 0:
            entry = entries_by_id[v['fileID']]
            if entry.__class_name == 'GameObject' or entry.m_GameObject['fileID'] == game_object:
              del entries_by_id[v['fileID']]  # remove to prevent top-level references
            v = type(v)(entry.get_serialized_properties_dict())
        v = resolve_properties(v, game_object, entries_by_id)
        r[k[1].upper() + k[2:]] = v
      else:
        r[k] = v
    return r
  elif isinstance(val, list):
    return type(val)(resolve_properties(x, game_object, entries_by_id) for x in val)
  return val


def load_prefab(args, scripts, file_path):
  pattern = f'**/{pathlib.Path(file_path).name}.prefab'
  for directory in args.directories:
    paths = list(pathlib.Path(directory).glob(pattern, case_sensitive=False))
    assert len(paths) <= 1, f'len(glob({pattern})) == {len(paths)}: {paths}'
    for p in paths:
      print(f'Loading {p.relative_to(directory)}')
      doc = unityparser.UnityDocument.load_yaml(p)
      entries_by_id: dict[int, unityparser.constants.UnityClass] = {int(e.anchor): e for e in doc.entries}
      prefab = {'Id': doc.entry.m_Name}

      for component in doc.entry.m_Component:
        entry = entries_by_id.pop(component['component']['fileID'], None)
        if not entry:  # already consumed
          continue
        if entry.__class_name != 'MonoBehaviour':
          continue
        cls = scripts.get(entry.m_Script['guid'])
        if not cls:  # probably a non-Timberborn script
          continue
        properties = entry.get_serialized_properties_dict()
        behaviour = resolve_properties(properties, int(doc.entry.anchor), entries_by_id)
        prefab[cls] = behaviour

      return prefab
  print(f'Missing prefab: {file_path}')
  return None
  assert False, f'Missing prefab: {file_path}'


def load_prefabs(args, scripts, factions):
  map = builtins.map if args.debug else concurrent.futures.ProcessPoolExecutor().map
  prefabs = {'common': {}}

  prefabcollections = load_specifications(args, 'prefabcollection')
  commonpaths = list(itertools.chain.from_iterable(c['Paths'] for c in prefabcollections))
  for prefab in map(load_prefab, *zip(*((args, scripts, prefab) for prefab in commonpaths))):
    if not prefab:
      continue
    assert prefab['Id'].lower() not in prefabs['common']
    prefabs['common'][prefab['Id'].lower()] = prefab

  for key, faction in factions.items():
    if faction['NewGameFullAvatar'].endswith('NO'):
      print(f'Skipping {faction['Id']} because avatar says NO')
      continue

    faction_prefabs = list(itertools.chain(
      faction['UniqueNaturalResources'],
      faction['CommonBuildings'],
      faction['UniqueBuildings'],
    ))
    prefabs[key] = {}
    for prefab in map(load_prefab, *zip(*((args, scripts, prefab) for prefab in faction_prefabs))):
      if not prefab:
        continue
      assert prefab['Id'].lower() not in prefabs[key]
      prefabs[key][prefab['Id'].lower()] = prefab
  return prefabs


def load_translations(args, language):
  catalog = {}
  for directory in args.directories:
    pattern = f'Resources/localizations/{language}*.txt'
    paths = list(pathlib.Path(directory).glob(pattern, case_sensitive=False))
    # assert len(paths) <= 1, f'len(glob({pattern})) == {len(paths)}: {paths}'
    for x in paths:
      with open(x, 'rt', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
          catalog[row['ID']] = row['Text']

  catalog['Pictogram.Science'] = '⚛️'
  catalog['Pictogram.Dwellers'] = '🛌'
  catalog['Pictogram.Workers'] = '🦫'
  catalog['Pictogram.Grows'] = '🌱'
  catalog['Pictogram.Dehydrates'] = '☠️'
  catalog['Pictogram.Drowns'] = '🌊'
  catalog['Pictogram.Matures'] = '🧺'
  catalog['Pictogram.Aquatic'] = '🌊'
  catalog['Pictogram.Plantable'] = '🌱'
  catalog['Pictogram.Cuttable'] = '🪚'
  catalog['Pictogram.Gatherable'] = '🧺'
  catalog['Pictogram.Ruin'] = '⛓️'

  def gettext(message):
    if message in catalog:
      return catalog[message]
    if message.endswith('DisplayName'):
      suffix = 's' if message.endswith('PluralDisplayName') else ''
      guess = message.rpartition('.')[0].rpartition('.')[2]
      return f'Untranslated: {guess}{suffix}'
    return f'Untranslated: {message}'

  return gettext


def dict_group_by_id(iterable, key):
  """Groups an interable of dicts into a dict of lists by the provided key."""
  groups = {}
  for value in iterable:
    group = value
    for key_part in key.split('.'):
      if key_part not in group:
        group = ''
        break
      group = group[key_part]
    groups.setdefault(group.lower(), []).append(value)
  return groups


class Generator:

  def __init__(self, gettext, faction, all_prefabs, goods, recipes, toolgroups):
    self.gettext = gettext
    self.faction = faction
    prefabs = list(all_prefabs['common'].values()) + list(all_prefabs[faction['Id'].lower()].values())
    self.prefabs = prefabs  # TODO: remove
    self.buildings_by_group = dict_group_by_id(prefabs, 'PlaceableBlockObject.ToolGroupId')
    self.natural_resources = sorted([p for p in prefabs if 'NaturalResource' in p], key=lambda p: p['NaturalResource']['OrderId'])
    self.plantable_by_group = dict_group_by_id(prefabs, 'Plantable.ResourceGroup')
    self.planter_building_by_group = dict_group_by_id(prefabs, 'PlanterBuilding.PlantableResourceGroup')
    cuttable_by_group = dict_group_by_id(prefabs, 'Cuttable.YielderSpecification.ResourceGroup')
    gatherable_by_group = dict_group_by_id(prefabs, 'Gatherable.YielderSpecification.ResourceGroup')
    scavengable_by_group = dict_group_by_id(prefabs, 'Ruin.YielderSpecification.ResourceGroup')
    self.yieldable_by_group = {}
    self.yieldable_by_group.update({k: ('Cuttable', v) for k, v in cuttable_by_group.items()})
    self.yieldable_by_group.update({k: ('Gatherable', v) for k, v in gatherable_by_group.items()})
    self.yieldable_by_group.update({k: ('Ruin', v) for k, v in scavengable_by_group.items()})
    self.goods = goods
    self.recipes = recipes
    self.toolgroups = toolgroups
    self.toolgroups_by_group = dict_group_by_id(toolgroups.values(), 'GroupId')

  def RenderFaction(self, faction):
    self.RenderNaturalResources(self.natural_resources)
    for g in self.toolgroups_by_group['']:
      self.RenderToolGroup(g)

  def RenderNaturalResources(self, resources):
    for r in resources:
      self.RenderNaturalResource(r)

  def RenderToolGroup(self, toolgroup):
    if toolgroup.get('Hidden'):
      return
    items = []
    for building in self.buildings_by_group.get(toolgroup['Id'].lower(), []):
      items.append((int(building['PlaceableBlockObject']['ToolOrder']), False, building))
    for tg in self.toolgroups_by_group.get(toolgroup['Id'].lower(), []):
      items.append((int(tg['Order']), True, tg))

    for _, is_group, item in sorted(items, key=lambda x: (x[0], x[1])):
      if is_group:
        self.RenderToolGroup(item)
      else:
        if item['PlaceableBlockObject'].get('DevModeTool'):
          continue
        self.RenderBuilding(item)

  def RenderBuilding(self, building):
    for r in building.get('Manufactory', {}).get('ProductionRecipeIds', []):
      self.RenderRecipe(self.recipes[r.lower()])

  def RenderNaturalResource(self, resource): ...
  def RenderRecipe(self, recipe): ...
  def Write(self, filename): ...


class GraphGenerator(Generator):

  def Write(self, filename):
    self.generate_graphs(filename, self.faction, self.prefabs, self.goods, self.recipes, self.toolgroups)

  def generate_graphs(self, filename, faction, prefabs, goods, recipes, toolgroups):
    def _(message):
      message = self.gettext(message)
      message = re.sub(r'<color=(\w+)>(.*?)</color>', r'<font color="\1">\2</font>', message, flags=re.S)
      if message.startswith('<') and message.endswith('>'):
        message = f'<{message}>'
      return message

    fontsize = 28
    g = pydot.Dot(
      faction['Id'],
      graph_type='digraph',
      label=_(faction['DisplayNameLocKey']),
      tooltip=' ',
      labelloc='t',
      fontsize=fontsize * 1.5,
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
    )
    g.set_node_defaults(
      tooltip=' ',
      fontsize=fontsize,
      penwidth=2,
      color='#a99262',
      fontcolor='white',
      fillcolor='#22362a',
      style='filled',
    )
    g.set_edge_defaults(
      tooltip=' ',
      labeltooltip=' ',
      fontsize=fontsize,
      penwidth=2,
      color='#a99262',
      fontcolor='white',
    )
    g.add_node(pydot.Node(
      'SciencePoints',
      label=_('Science.SciencePoints'),
      # image='sprites/bottombar/buildinggroups/Science.png',
    ))

    for building in prefabs:
      if building.get('PlaceableBlockObject', {}).get('ToolGroupId', '').lower() not in toolgroups:
        continue
      toolgroup = toolgroups[building['PlaceableBlockObject']['ToolGroupId'].lower()]
      if toolgroup.get('Hidden'):
        continue

      building_goods = set()
      for c in building.get('Building', {}).get('BuildingCost', []):
        building_goods.add(c['GoodId'])

      for r in building.get('Manufactory', {}).get('ProductionRecipeIds', []):
        if r.lower() not in recipes:
          breakpoint()
        recipe = recipes[r.lower()]

        sg = pydot.Subgraph(
          building['Id'],
          cluster=True,
          label=f'[{_(toolgroup['NameLocKey'])}]\n{_(building['LabeledPrefab']['DisplayNameLocKey'])}',
          fontsize=fontsize,
        )
        g.add_subgraph(sg)

        sg.add_node(pydot.Node(
          building['Id'] + '.' + recipe['Id'],
          label=f'{_('Time.HoursShort').format(recipe['CycleDurationInHours'])}',
          tooltip=_(recipe['DisplayLocKey']),
        ))

        if recipe['Fuel']['Id']:
          good = goods[recipe['Fuel']['Id'].lower()]
          g.add_edge(pydot.Edge(
            good['Id'],
            building['Id'] + '.' + recipe['Id'],
            label=round(1 / recipe['CyclesFuelLasts'], 3),
            labeltooltip=f'{_(good['DisplayNameLocKey'])} --> {_(recipe['DisplayLocKey'])}',
            style='dashed' if good['Id'] in building_goods else 'solid',
            color='#b30000',
          ))

        for x in recipe['Ingredients']:
          if x['Good']['Id'].lower() not in goods:
            continue
          good = goods[x['Good']['Id'].lower()]
          label = _(good['DisplayNameLocKey'])
          #if good['Id'] in building_goods:
          #  continue
          g.add_node(pydot.Node(
            good['Id'],
            label=label,
            # image=f'sprites/goods/{good['Good']['Id']}Icon.png',
          ))
          g.add_edge(pydot.Edge(
            good['Id'],
            building['Id'] + '.' + recipe['Id'],
            label=x['Amount'],
            style='dashed' if good['Id'] in building_goods else 'solid',
            color='#b30000',
          ))

        for x in recipe['Products']:
          if x['Good']['Id'].lower() not in goods:
            continue
          good = goods[x['Good']['Id'].lower()]
          label = _(good['DisplayNameLocKey'])
          g.add_node(pydot.Node(
            good['Id'],
            label=label,
            # image=f'sprites/goods/{good['Good']['Id']}Icon.png',
          ))
          g.add_edge(pydot.Edge(
            building['Id'] + '.' + recipe['Id'],
            good['Id'],
            label=x['Amount'],
            color='#008000',
          ))

        if recipe['ProducedSciencePoints'] > 0:
          g.add_edge(pydot.Edge(
            building['Id'] + '.' + recipe['Id'],
            'SciencePoints',
            label=recipe['ProducedSciencePoints'],
            color='#008000',
          ))

    g.write(f'{filename}.dot', format='raw')
    g.write(f'{filename}.svg', format='svg')


class HtmlGenerator(Generator):

  @contextlib.contextmanager
  def tag(self, tag_name, *args, **kwargs):
    t = self.doc.tag(tag_name, *args, **kwargs)
    def checkpoint():
      nonlocal content
      content = len(self.doc.result)
    start = len(self.doc.result)
    with t:
      content = len(self.doc.result)
      yield checkpoint
      end = len(self.doc.result)
    if end == content:
      del self.doc.result[start:]

  def RenderFaction(self, faction, filename):
    _ = self.gettext
    tag = self.doc.tag
    line = self.doc.line
    name = _(faction['DisplayNameLocKey'])
    with tag('html'):
      with tag('head'):
        with tag('meta', charset='utf-8'):
          pass
        line('title', name)
        with tag('style'):
          self.doc.asis(r'''
body, .content {
  background-color: #22362a;
  color: white;
  width: fit-content;
}
.toolgroup, .building, .recipe {
  border: #a99262 solid 2px;
  padding: 4px;
  margin: 4px;
}
.toolgroup {
  background-color: #1d2c38;
}
.building {
  background-color: #322227;
}
.recipe {
  background-color: #22362a;
}
table {
  width: 100%;
  border-collapse: collapse;
}
tr:nth-child(even) {
  background-color: rgb(255 255 255 / 0.1);
}
tr > :not(.name) {
  padding-inline-start: 12px;
  text-align: right;
}
.header, .stats {
  display: flex;
  justify-content: space-between;
}
.name {
    margin-inline-end: 5px;
}
.stats div {
  font-size: larger;
  margin-inline-start: 6px;
}
ul {
  margin: 0px;
  padding-inline-start: 20px;
}
ul.cost, ul.ingredients {
  list-style: "▶ ";
}
ul.cost li::marker, ul.ingredients li::marker {
  color: #b30000;
}
ul.products {
  list-style: "◀ ";
}
ul.products li::marker {
  color: #008000;
}
''')
      with tag('body'):
        line('h1', name)
        with self.tag('div', klass='content') as t:
          super().RenderFaction(faction)
        # with tag('object', width='1440', data=str(filename.relative_to(filename.parent).with_suffix('.svg'))):
        #   pass

  def RenderNaturalResources(self, resources):
    _ = self.gettext
    line = self.doc.line
    with self.tag('div', klass='toolgroup'):
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

  def RenderNaturalResource(self, r):
    _ = self.gettext
    line = self.doc.line
    plantable = r.get('Plantable')
    if all([self.toolgroups[x['PlaceableBlockObject']['ToolGroupId'].lower()].get('Hidden') for x in self.planter_building_by_group[plantable['ResourceGroup'].lower()]]):
      return
    with self.tag('tr', klass='naturalresource'):
      line('td', _(f'Pictogram.Aquatic') if r['WaterNaturalResourceSpecification']['MinWaterHeight'] > 0 else '', klass='name')
      line('td', _(r['LabeledPrefab']['DisplayNameLocKey']), klass='name')
      line('td', f'{_('Time.DaysShort').format(r['Growable']['GrowthTimeInDays'])}')
      line('td', f'{_('Time.DaysShort').format(r['WateredNaturalResourceSpecification']['DaysToDieDry'])}')
      line('td', f'{_('Time.DaysShort').format(r['WaterNaturalResourceSpecification']['DaysToDie'])}')
      if 'Gatherable' in r:
        line('td', f'{_('Time.DaysShort').format(r['Gatherable']['YieldGrowthTimeInDays'])}')
      else:
        line('td', '')

      super().RenderNaturalResource(r)

  def RenderToolGroup(self, toolgroup):
    _ = self.gettext
    line = self.doc.line
    with self.tag('div', klass='toolgroup') as t:
      line('div', _(toolgroup['NameLocKey']), klass='name')
      t()
      super().RenderToolGroup(toolgroup)

  def RenderBuilding(self, building):
    _ = self.gettext
    line = self.doc.line
    with self.tag('div', klass='building') as t:
      force_show = False
      with self.tag('div', klass='header') as h:
        name = _(building['LabeledPrefab']['DisplayNameLocKey']).replace('\n', ' ')
        line('div', name, klass='name')
        with self.tag('div', klass='stats'):
          if 'Dwelling' in building:
            line('div', f'{building['Dwelling']['MaxBeavers']}{_(f'Pictogram.Dwellers')}', klass='dwelling')
            force_show = True
          if 'WorkplaceSpecification' in building:
            line('div', f'{building['WorkplaceSpecification']['MaxWorkers']}{_(f'Pictogram.Workers')}', klass='workers')
            force_show = True
          if building['Building']['ScienceCost'] > 0:
            science = building['Building']['ScienceCost']
            if science >= 1000:
              science = f'{science / 1000:n}k'
            line('div', f'{science}{_(f'Pictogram.Science')}', klass='science')
            force_show = True
      if not force_show:
        t()

      with self.tag('ul', klass='cost'):
        for x in reversed(building['Building']['BuildingCost']):
          good = self.goods[x['GoodId'].lower()]
          lockey = 'DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'
          label = _(good[lockey])
          line('li', f'{x['Amount']} {label}')

      resources = {}
      with self.tag('table') as t:
        with self.tag('tr'):
          line('th', '', klass='name')
          plantable = building.get('PlanterBuilding')
          if plantable:
            plants = self.plantable_by_group[plantable['PlantableResourceGroup'].lower()]
            for p in plants:
              resources[p['LabeledPrefab']['DisplayNameLocKey']] = p
            line('th', _(f'Pictogram.Plantable'))
          else:
            plants = None
          yieldable = building.get('YieldRemovingBuilding')
          if yieldable:
            yield_type, yields = self.yieldable_by_group[yieldable['ResourceGroup'].lower()]
            for y in yields:
              yplantable = y.get('Plantable')
              if yplantable and all([self.toolgroups[x['PlaceableBlockObject']['ToolGroupId'].lower()].get('Hidden') for x in self.planter_building_by_group[yplantable['ResourceGroup'].lower()]]):
                continue
              resources[y['LabeledPrefab']['DisplayNameLocKey']] = y
            line('th', _(f'Pictogram.{yield_type}'))
          else:
            yield_type, yields = None, None
        t()

        for r in sorted(resources.items(), key=lambda r: r[1].get('NaturalResource', {}).get('OrderId', 0)):
          plant = r[1]
          with self.tag('tr'):
            line('td', _(plant['LabeledPrefab']['DisplayNameLocKey']), klass='name')
            if plants:
              if plant in plants:
                line('td', _('Time.HoursShort').format(plant['Plantable']['PlantTimeInHours']))
              else:
                line('td', '')
            if yields:
              if plant in yields:
                line('td', _('Time.HoursShort').format(plant[yield_type]['YielderSpecification']['RemovalTimeInHours']))
              else:
                line('td', '')

      super().RenderBuilding(building)

  def RenderRecipe(self, recipe):
    _ = self.gettext
    line = self.doc.line
    with self.tag('div', klass='recipe') as t:
      name = _(recipe['DisplayLocKey'])
      with self.tag('div', klass='header'):
        line('div', name, klass='name')
        with self.tag('div', klass='stats'):
          line('div', f'{_('Time.HoursShort').format(recipe['CycleDurationInHours'])}', klass='duration')
      t()

      with self.tag('ul', klass='ingredients'):
        if recipe['Fuel']['Id']:
          good = self.goods[recipe['Fuel']['Id'].lower()]
          amount = round(1 / recipe['CyclesFuelLasts'], 3)
          lockey = 'DisplayNameLocKey' if amount == 1 else 'PluralDisplayNameLocKey'
          line('li', f'{amount} {_(good[lockey])}')

        for x in recipe['Ingredients']:
          if x['Good']['Id'].lower() not in self.goods:
            continue
          good = self.goods[x['Good']['Id'].lower()]
          lockey = 'DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'
          label = _(good[lockey])
          line('li', f'{x['Amount']} {label}')

      with self.tag('ul', klass='products'):
        for x in recipe['Products']:
          if x['Good']['Id'].lower() not in self.goods:
            continue
          good = self.goods[x['Good']['Id'].lower()]
          lockey = 'DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'
          label = _(good[lockey])
          line('li', f'{x['Amount']} {label}')

        if recipe['ProducedSciencePoints'] > 0:
          line('li', f'{recipe['ProducedSciencePoints']} {_('Science.SciencePoints')}')

      super().RenderRecipe(recipe)

  def Write(self, filename):
    self.doc = yattag.Doc()
    self.doc.asis('<!DOCTYPE html>')
    self.RenderFaction(self.faction, pathlib.Path(filename))
    with open(f'{filename}.html', 'wt') as f:
      print(yattag.indent(self.doc.getvalue()), file=f)

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

  def RenderFaction(self, faction):
    _ = self.gettext
    name = _(faction['DisplayNameLocKey'])
    self.stack = [[
      name,
      '-' * len(name),
    ]]
    super().RenderFaction(faction)

  def RenderNaturalResources(self, resources):
    _ = self.gettext
    with self.NewContext(f'{self.prefix}{_('MapEditor.Layers.NaturalResources')}:') as c:
      super().RenderNaturalResources(resources)

  def RenderNaturalResource(self, r):
    _ = self.gettext
    plantable = r.get('Plantable')
    if all([self.toolgroups[x['PlaceableBlockObject']['ToolGroupId'].lower()].get('Hidden') for x in self.planter_building_by_group[plantable['ResourceGroup'].lower()]]):
      return

    name = _(r['LabeledPrefab']['DisplayNameLocKey'])
    if r['WaterNaturalResourceSpecification']['MinWaterHeight'] > 0:
      name = f'{_(f'Pictogram.Aquatic')} {name}'
    stats = [
      f'{_('Time.DaysShort').format(r['Growable']['GrowthTimeInDays'])}{_(f'Pictogram.Grows')}',
      f'{_('Time.DaysShort').format(r['WateredNaturalResourceSpecification']['DaysToDieDry'])}{_(f'Pictogram.Dehydrates')}',
      f'{_('Time.DaysShort').format(r['WaterNaturalResourceSpecification']['DaysToDie'])}{_(f'Pictogram.Drowns')}',
    ]
    if 'Gatherable' in r:
      stats.append(f'{_('Time.DaysShort').format(r['Gatherable']['YieldGrowthTimeInDays'])}{_(f'Pictogram.Matures')}')

    heading = f'{self.prefix}{name} [{' '.join(stats)}]'
    with self.NewContext(heading, forced=True) as c:
      super().RenderNaturalResource(r)

  def RenderToolGroup(self, toolgroup):
    _ = self.gettext
    with self.NewContext(f'{self.prefix}{_(toolgroup['NameLocKey'])}:') as c:
      super().RenderToolGroup(toolgroup)

  def RenderBuilding(self, building):
    _ = self.gettext
    text = _(building['LabeledPrefab']['DisplayNameLocKey']).replace('\n', ' ')
    stats = []
    if 'Dwelling' in building:
      stats.append(f'{building['Dwelling']['MaxBeavers']}{_(f'Pictogram.Dwellers')}')
    if 'WorkplaceSpecification' in building:
      stats.append(f'{building['WorkplaceSpecification']['MaxWorkers']}{_(f'Pictogram.Workers')}')
    if building['Building']['ScienceCost'] > 0:
      science = building['Building']['ScienceCost']
      if science >= 1000:
        science = f'{science / 1000:n}k'
      stats.append(f'{science}{_(f'Pictogram.Science')}')
    if stats:
      text += f' [{' '.join(stats)}]'
    heading = f'{self.prefix}{text}:'
    with self.NewContext(heading) as c:
      for x in reversed(building['Building']['BuildingCost']):
        good = self.goods[x['GoodId'].lower()]
        lockey = 'DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'
        label = _(good[lockey])
        c.append(f'{self.prefix}▶ {x['Amount']} {label}')

      resources = {}
      plantable = building.get('PlanterBuilding')
      if plantable:
        plants = self.plantable_by_group[plantable['PlantableResourceGroup'].lower()]
        for p in plants:
          resources[p['LabeledPrefab']['DisplayNameLocKey']] = p
      else:
        plants = None
      yieldable = building.get('YieldRemovingBuilding')
      if yieldable:
        yield_type, yields = self.yieldable_by_group[yieldable['ResourceGroup'].lower()]
        for y in yields:
          yplantable = y.get('Plantable')
          if yplantable and all([self.toolgroups[x['PlaceableBlockObject']['ToolGroupId'].lower()].get('Hidden') for x in self.planter_building_by_group[yplantable['ResourceGroup'].lower()]]):
            continue
          resources[y['LabeledPrefab']['DisplayNameLocKey']] = y
      else:
        yield_type, yields = None, None

      for r in sorted(resources.items(), key=lambda r: r[1].get('NaturalResource', {}).get('OrderId', 0)):
        plant = r[1]
        text = _(plant['LabeledPrefab']['DisplayNameLocKey'])
        stats = []
        if plants:
          if plant in plants:
            stats.append(f'{_('Time.HoursShort').format(plant['Plantable']['PlantTimeInHours'])}{_(f'Pictogram.Plantable')}')
        if yields:
          if plant in yields:
            stats.append(f'{_('Time.HoursShort').format(plant[yield_type]['YielderSpecification']['RemovalTimeInHours'])}{_(f'Pictogram.{yield_type}')}')
        if stats:
          text += f' [{' '.join(stats)}]'
        c.append(f'{self.prefix}{text}')

      super().RenderBuilding(building)

    if not c and stats:
      with self.NewContext(heading[:-1], forced=True) as c:
        pass

  def RenderRecipe(self, recipe):
    _ = self.gettext
    with self.NewContext(f'{self.prefix}{_(recipe['DisplayLocKey'])} [{_('Time.HoursShort').format(recipe['CycleDurationInHours'])}]') as c:
      if recipe['Fuel']['Id']:
        good = self.goods[recipe['Fuel']['Id'].lower()]
        amount = round(1 / recipe['CyclesFuelLasts'], 3)
        lockey = 'DisplayNameLocKey' if amount == 1 else 'PluralDisplayNameLocKey'
        c.append(f'{self.prefix}▶ {amount} {_(good[lockey])}')

      for x in recipe['Ingredients']:
        if x['Good']['Id'].lower() not in self.goods:
          continue
        good = self.goods[x['Good']['Id'].lower()]
        lockey = 'DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'
        label = _(good[lockey])
        c.append(f'{self.prefix}▶ {x['Amount']} {label}')

      for x in recipe['Products']:
        if x['Good']['Id'].lower() not in self.goods:
          continue
        good = self.goods[x['Good']['Id'].lower()]
        lockey = 'DisplayNameLocKey' if x['Amount'] == 1 else 'PluralDisplayNameLocKey'
        label = _(good[lockey])
        c.append(f'{self.prefix}◀ {x['Amount']} {label}')

      if recipe['ProducedSciencePoints'] > 0:
        c.append(f'{self.prefix}◀ {recipe['ProducedSciencePoints']} {_('Science.SciencePoints')}')

      super().RenderRecipe(recipe)

  def Write(self, filename):
    self.RenderFaction(self.faction)
    lines, = self.stack
    with open(f'{filename}.txt', 'wt') as f:
      for line in lines:
        print(line, file=f)


def main():
  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument('-D', '--debug', help='debug mode', action='store_true')
  parser.add_argument('-d', '--directory', help='location of extracted resources', action='append', dest='directories', default=[])
  hparser = argparse.ArgumentParser(parents=[parser], add_help=False)
  hparser.add_argument('-l', '--language')
  hparser.add_argument('-h', '--help', action='store_true')
  args = hparser.parse_args()

  languages = []
  for directory in args.directories:
    pattern = f'Resources/localizations/*.txt'
    for p in list(pathlib.Path(directory).glob(pattern, case_sensitive=False)):
      if p.match('*_*') or p.match('reference*'):
        continue
      languages.append(p.relative_to(directory).stem)
    languages.sort(key=lambda x: (len(x), x))

  parser.add_argument('-l', '--language', help=f'localization language to use (valid options: {', '.join(['all'] + languages)})')
  parser = argparse.ArgumentParser(parents=[parser])
  args = parser.parse_args()

  if args.language == 'all':
    args.languages = languages
  else:
    args.languages = [l.strip() for l in (args.language or '').split(',') if l.strip()] or ['enUS']
  for l in args.languages:
    if l not in languages:
      parser.error(f'argument -l/--language: invalid choice: {l!r} (choose from {', '.join(['all'] + languages)})')

  cached = False
  cache_file = f'.cache.{hashlib.sha256(repr(args.directories).encode()).hexdigest()}'
  try:
    with open(cache_file, 'rb') as f:
      print(f'Loading {cache_file}')
      d = pickle.load(f)

      if d['directories'] == args.directories:
        prefabs = d['prefabs']
        factions = d['factions']
        goods = d['goods']
        recipes = d['recipes']
        toolgroups = d['toolgroups']
        if factions and prefabs and recipes and goods and toolgroups:
          cached = True
  except:
    print(f'Missing/corrupt: {cache_file}')

  if not cached or args.debug:
    factions = {
      f['Id'].lower(): f
      for f in sorted(load_specifications(args, 'faction'), key=lambda f: f['Order'])
    }
    goods = {
      g['Id'].lower(): g
      for g in load_specifications(args, 'good')
    }
    recipes = {
      r['Id'].lower(): r
      for r in load_specifications(args, 'recipe')
    }
    toolgroups_by_id = {tg['Id'].lower(): tg for tg in load_specifications(args, 'toolgroup')}
    def ToolGroupKey(g):
      k = (int(g['Order']),)
      groupId = g.get('GroupId')
      if groupId:
        k = ToolGroupKey(toolgroups_by_id[groupId.lower()]) + k
      return k
    toolgroups = {tg['Id'].lower(): tg for tg in sorted(toolgroups_by_id.values(), key=lambda kg: ToolGroupKey(kg))}
    scripts = load_metadata(args, 'scripts/timberborn.*/**/*.cs')
    prefabs = load_prefabs(args, scripts, factions)
    d = dict(
      directories=args.directories,
      prefabs=prefabs,
      factions=factions,
      goods=goods,
      recipes=recipes,
      toolgroups=toolgroups,
    )
    with open(cache_file, 'wb') as f:
      pickle.dump(d, f, protocol=pickle.HIGHEST_PROTOCOL)
    with open(cache_file + '.json', 'wt') as f:
      json5.dump(d, f, indent=2, quote_keys=True, trailing_commas=False)

  generators = (
    TextGenerator,
    HtmlGenerator,
    GraphGenerator,
  )
  for language in args.languages:
    _ = load_translations(args, language)
    for faction in factions.values():
      if faction['NewGameFullAvatar'].endswith('NO'):
        print(f'Skipping {faction['Id']} in {_('Settings.Language.Name')}: {_(faction['DisplayNameLocKey'])}')
        continue
      print(f'Generating {faction['Id']} in {_('Settings.Language.Name')}: {_(faction['DisplayNameLocKey'])}')
      for cls in generators:
        gen = cls(_, faction, prefabs, goods, recipes, toolgroups)
        gen.Write(f'out/{language}_{faction['Id']}')


if __name__ == '__main__':
  main()
