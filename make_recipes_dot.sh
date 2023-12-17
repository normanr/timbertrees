#!/bin/bash

process_recipe()
{
	#echo recipes "$@"
	local building=${1#ExportedProject/Assets/Resources/*/*/*/}
	local x
	for x in ExportedProject/Assets/Resources/specifications/recipes/RecipeSpecification.$2.*; do
		if [[ ! $x =~ ^ExportedProject/Assets/Resources/specifications/recipes/RecipeSpecification\.$2\.[^.]*$ ]]; then
			continue
		fi
		# + .Id + "\\n"
		jq -r '
			(.Ingredients[] | "  \"" + .Good.Id + "\" [label=<<table border=\"0\" cellpadding=\"0\" cellspacing=\"0\"><tr><td><img src=\"ExportedProject/Assets/Resources/sprites/goods/" + .Good.Id + "Icon.png\"/></td><td>" + .Good.Id + "</td></tr></table>>]"),
			({Id:.Id,Ingredient:.Ingredients[]} | "  \"" + .Ingredient.Good.Id + "\" -> \"'$building'." + .Id + "\" [label=\"" + (.Ingredient.Amount | tostring) + "\"]"),
			("  \"'$building'." + .Id + "\" [shape=rectangle label=<<table border=\"0\" cellpadding=\"0\" cellspacing=\"0\"><tr><td rowspan=\"2\"><img src=\"'$1'Icon.png\"/></td><td>'$building'</td></tr><tr><td>" + (.CycleDurationInHours | tostring) + "h</td></tr></table>>]"),
			({Id:.Id,Product:.Products[]} | "  \"'$building'." + .Id + "\" -> \"" + .Product.Good.Id + "\" [label=\"" + (.Product.Amount | tostring) + "\"]"),
			(.Products[] | "  \"" + .Good.Id + "\" [label=<<table border=\"0\" cellpadding=\"0\" cellspacing=\"0\"><tr><td><img src=\"ExportedProject/Assets/Resources/sprites/goods/" + .Good.Id + "Icon.png\"/></td><td>" + .Good.Id + "</td></tr></table>>]"),
			(select(.ProducedSciencePoints > 0) | "  \"'$building'." + .Id + "\" -> \"Science\" [label=\"" + (.ProducedSciencePoints | tostring) + "\"]")
			' $x
	done
}

process_buildings()
{
	local x
	for x in ExportedProject/Assets/Resources/buildings/*/*/*.$1.prefab; do
		if [[ ! $x =~ ^ExportedProject/Assets/Resources/buildings/[^/]*/[^/]*/[^.]*\.$1\.prefab$ ]]; then
			continue
		fi
		recipes=($(sed -e 's/!u!\([^ ]\+\)/!<tag:unity3d.com,2011:\1>/' $x \
			| yq e '.[] | select(._productionRecipeIds) | ._productionRecipeIds[]' -))
		x=${x%.$1.prefab}
		for recipe in ${recipes[@]}; do
			process_recipe $x ${recipe}
		done
	done
	echo "  \"Science\" [label=<<table border=\"0\" cellpadding=\"0\" cellspacing=\"0\"><tr><td><img src=\"ExportedProject/Assets/Resources/sprites/bottombar/buildinggroups/Science.png\"/></td><td>Science</td></tr></table>>]"
}

faction() {
	(
		echo "digraph recipes {"
		echo "  label=\""$1"\""
		echo "  labelloc=t"
		echo "  fontsize=24"
		echo "  rankdir=LR"
		process_buildings $1  # | sort -u
		echo "}"
	) > recipes_$1.dot
	dot -Tsvg recipes_$1.dot > recipes_$1.svg
}

cd $(dirname $0)

#buildings Folktails
#buildings IronTeeth
faction Folktails
faction IronTeeth
