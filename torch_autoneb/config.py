from torch import optim
from torch.optim import lr_scheduler

import torch_autoneb


def _with_new_keys(config_dict: dict) -> dict:
    return {key.replace("_", "-"): value for key, value in config_dict.items()}


def _replace_instanciation(config, package):
    if isinstance(config, dict):
        # Name + args
        name = config["name"]
        del config["name"]
        return getattr(package, name), config
    else:
        # Just the name
        return getattr(package, config), {}


def _deep_update(source: dict, target: dict):
    for key, value in target.items():
        if key in source and isinstance(value, dict) and key != "args":
            _deep_update(source[key], value)
        else:
            source[key] = value


class EvalConfig:
    def __init__(self, batch_size: int):
        self.batch_size = batch_size

    @staticmethod
    def from_dict(config_dict: dict):
        return EvalConfig(**_with_new_keys(config_dict))


class OptimConfig:
    def __init__(self, nsteps: int, optim_type, optim_args: dict, scheduler_type, scheduler_args: dict, eval_config: EvalConfig):
        self.nsteps = nsteps
        self.optim_type = optim_type
        self.optim_args = optim_args
        self.scheduler_type = scheduler_type
        self.scheduler_args = scheduler_args
        self.eval_config = eval_config

    @staticmethod
    def from_dict(config_dict: dict):
        config_dict = _with_new_keys(config_dict)
        config_dict["optim_type"], config_dict["optim_args"] = _replace_instanciation(config_dict, "algorithm", optim)
        config_dict["scheduler_type"], config_dict["scheduler_args"] = _replace_instanciation(config_dict, "scheduler", lr_scheduler)
        config_dict["eval_config"] = EvalConfig.from_dict(config_dict["eval_config"])
        return OptimConfig(**config_dict)


class NEBConfig:
    def __init__(self, spring_constant: float, weight_decay: float, insert_method: callable, insert_args: dict, subsample_pivot_count: int, optim_config: OptimConfig):
        self.spring_constant = spring_constant
        self.weight_decay = weight_decay
        self.insert_args = insert_args
        self.insert_method = insert_method
        self.subsample_pivot_count = subsample_pivot_count
        self.optim_config = optim_config

    @staticmethod
    def from_dict(config_dict: dict):
        config_dict = _with_new_keys(config_dict)
        config_dict["insert_method"], config_dict["insert_args"] = _replace_instanciation(config_dict["insert"], torch_autoneb.fill)
        return NEBConfig(**config_dict)


class AutoNEBConfig:
    def __init__(self, neb_configs: list):
        self.cycle_count = len(neb_configs)
        self.neb_configs = neb_configs

    @staticmethod
    def from_list(configs_list: iter):
        current_state = {}
        cycles = []
        for cycle in configs_list:
            _deep_update(current_state, _with_new_keys(cycle))
            cycles.append(NEBConfig.from_dict(current_state))
        return AutoNEBConfig(cycles)


class LandscapeExplorationConfig:
    def __init__(self, value_key: str, weight_key: str, suggest_methods: list, suggest_args: list, auto_neb_config: AutoNEBConfig):
        self.value_key = value_key
        self.weight_key = weight_key
        self.suggest_methods = suggest_methods
        self.suggest_args = suggest_args
        self.auto_neb_config = auto_neb_config

    @staticmethod
    def from_dict(config_dict: dict):
        config_dict = _with_new_keys(config_dict)
        config_dict["suggest_methods"], config_dict["suggest_args"] = zip(*[_replace_instanciation(engine, torch_autoneb.suggest) for engine in config_dict["suggest"]])
        config_dict["auto_neb_config"] = AutoNEBConfig.from_list(config_dict["autoneb"])
        return LandscapeExplorationConfig(**config_dict)