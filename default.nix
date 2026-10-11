{
  lib,
  python3,
}:

let
  ps = python3.pkgs;
in
ps.buildPythonApplication {
  pname = "morphism-gen";
  version = "0.1.0";
  pyproject = true;
  src = lib.cleanSource ./.;

  build-system = [ ps.setuptools ];

  dependencies = [
    ps.materialyoucolor
    ps.pillow
  ];

  pythonImportsCheck = [ "morphism_gen" ];

  meta = {
    description = "Standalone Material You theme generator with caelestia-exact colour extraction";
    homepage = "https://github.com/roccoflac/morphism-gen";
    license = lib.licenses.gpl3Only;
    mainProgram = "morphism-gen";
    platforms = lib.platforms.linux;
  };
}
