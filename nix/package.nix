{ python3Packages }:
python3Packages.buildPythonApplication {
  pname = "ctx-voice";
  version = "0.1.0";
  src = ../.;
  pyproject = true;
  build-system = [ python3Packages.setuptools ];
  propagatedBuildInputs = with python3Packages; [ numpy sounddevice soundfile ];
  pythonImportsCheck = [ "voice_ai" ];
  doCheck = false; # CI runs stdlib tests separately.
}
