[
{
    "property-id" "tag:staff@noreply.openkim.org,2014-05-21:property/elastic-constants-isothermal-cubic-crystal-npt"
    "instance-id" 1

    "short-name" {
        "source-value"  ["@<crystal_structure>@"]
    }
    "species" {
        "source-value"  ["@<species>@"]
    }
    "a" {
        "source-value"  @<lattice_constant>@
        "source-unit"   "angstrom"
    }
    "basis-atom-coordinates" {
        "source-value"  @<basis_coordinates>@
    }
    "space-group"  {
        "source-value"  "@<space_group>@"
    }
    "temperature" {
        "source-value"  0
        "source-unit"  "K"
    }
    "cauchy-stress"  {
        "source-value"  [0 0 0 0 0 0]
        "source-unit"   "GPa"
    }
    "c11" {
        "source-value"  @<C11>@
        "source-unit"   "@<units>@"
        "source-std-uncert-value"  @<C11_sig>@
    }
    "c12" {
        "source-value"  @<C12>@
        "source-unit"   "@<units>@"
        "source-std-uncert-value"  @<C12_sig>@
    }
    "c44" {
        "source-value"  @<C44>@
        "source-unit"   "@<units>@"
        "source-std-uncert-value"  @<C44_sig>@
    }
    "excess" {
        "source-value"  @<excess>@
        "source-unit"   "@<units>@"
        "source-std-uncert-value"  @<excess_sig>@
    }
}

{
    "property-id" "tag:staff@noreply.openkim.org,2014-04-15:property/bulk-modulus-isothermal-cubic-crystal-npt"
    "instance-id" 2

    "short-name" {
        "source-value"  ["@<crystal_structure>@"]
    }
    "species" {
        "source-value"  ["@<species>@"]
    }
    "a" {
        "source-value"  @<lattice_constant>@
        "source-unit"   "angstrom"
    }
    "basis-atom-coordinates" {
        "source-value"  @<basis_coordinates>@
    }
    "space-group"  {
        "source-value"  "@<space_group>@"
    }
    "temperature" {
        "source-value"  0
        "source-unit"  "K"
    }
    "cauchy-stress"  {
        "source-value"  [0 0 0 0 0 0]
        "source-unit"   "GPa"
    }
    "isothermal-bulk-modulus" {
        "source-value"  @<B>@
        "source-unit"   "@<units>@"
        "source-std-uncert-value"  @<B_sig>@
    }
}
]
