[{
    "property-id" "tag:staff@noreply.openkim.org,2014-05-21:property/surface-energy-broken-bond-fit-cubic-bravais-crystal-npt"
    "instance-id" 1

    "short-name" {
        "source-value"  ["@<crystal_structure>@"]
    }
    "species" {
        "source-value"  [ "@<element>@" ]
    }
    "a" {
        "source-value"  @<lattice_constant>@
        "source-unit"   "angstrom"
    }
    "space-group" {
        "source-value"  "@<space_group>@"
    }
    "temperature" {
        "source-value"  0
        "source-unit"   "K"
    }
    "cauchy-stress" {
        "source-value"  [ 0 0 0 0 0 0 ]
        "source-unit"   "GPa"
    }
    "fit-c" {
        "source-value"  @<CorrectionParameter>@
        "source-unit"   "eV/angstrom^2"
    }
    "fit-p1" {
        "source-value"  @<BrokenBond_P1>@
        "source-unit"   "eV/angstrom^2"
    }
    "fit-p2" {
        "source-value"  @<BrokenBond_P2>@
        "source-unit"   "eV/angstrom^2"
    }
    "fit-p3" {
        "source-value"  @<BrokenBond_P3>@
        "source-unit"   "eV/angstrom^2"
    }
    "fit-error-max" {
        "source-value"  @<ErrorRange>@
    }
    "fit-error-range" {
        "source-value"  @<MaxResidual>@
    }
}

@[ for energy in energies ]@
{
    "property-id" "tag:staff@noreply.openkim.org,2014-05-21:property/surface-energy-cubic-crystal-npt"
    "instance-id" @<energy.index>@

    "short-name" {
        "source-value"  ["@<crystal_structure>@"]
    }
    "species" {
        "source-value"  [ "@<element>@" ]
    }
    "a" {
        "source-value"  @<lattice_constant>@
        "source-unit"   "angstrom"
    }
    "space-group" {
        "source-value"  "@<space_group>@"
    }
    "temperature" {
        "source-value"  0
        "source-unit"   "K"
    }
    "cauchy-stress" {
        "source-value"  [ 0 0 0 0 0 0 ]
        "source-unit"   "GPa"
    }
    "basis-atom-coordinates" {
        "source-value"  @<basis_atoms>@
    }

    "miller-indices" {
        "source-value"  @<energy.miller_index|jsonl>@
    }
    "surface-energy" {
        "source-value"  @<energy.surface_energy>@
        "source-unit"   "eV/angstrom^2"
    }
    "relaxed-surface-positions" {
        "source-value"  @<energy.positions|json>@
        "source-unit"   "angstrom"
    }
}
@[ endfor ]@

@[ for energy in unrelaxedenergies ]@
{
    "property-id" "tag:staff@noreply.openkim.org,2014-05-21:property/surface-energy-ideal-cubic-crystal"
    "instance-id" @<energy.index>@

    "short-name" {
        "source-value"  ["@<crystal_structure>@"]
    }
    "species" {
        "source-value"  ["@<element>@"]
    }
    "a" {
        "source-value"  @<lattice_constant>@
        "source-unit"   "angstrom"
    }
    "space-group" {
        "source-value"  "@<space_group>@"
    }
    "cauchy-stress" {
        "source-value"  [ 0 0 0 0 0 0 ]
        "source-unit"   "GPa"
    }
    "basis-atom-coordinates" {
        "source-value"  @<basis_atoms>@
    }

    "miller-indices" {
        "source-value"  @<energy.miller_index|jsonl>@
    }
    "ideal-surface-energy" {
        "source-value"  @<energy.surface_energy>@
        "source-unit"   "eV/angstrom^2"
    }
}
@[ endfor ]@
]
