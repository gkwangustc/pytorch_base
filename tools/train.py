from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

__dir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.append(__dir__)
sys.path.insert(0, os.path.abspath(os.path.join(__dir__, "..")))

import torch
import torch.distributed as dist

from core.data import build_dataloader
from core.modeling import build_model
from core.losses import build_loss
from core.optimizer import build_optimizer
from core.postprocess import build_post_process
from core.metrics import build_metric
from core.utils.save_load import load_model
from core.utils.utility import set_seed
import tools.program as program


def main(config, device, logger, log_writer):
    global_config = config["Global"]

    # build dataloader
    train_dataloader = build_dataloader(config, "Train", device, logger)
    if len(train_dataloader) == 0:
        logger.error(
            "No Images in train dataset, please ensure\n"
            + "\t1. The images num in the train label_file_list should be larger than or equal with batch size.\n"
            + "\t2. The annotation file and path in the configuration file are provided normally."
        )
        return

    if config["Eval"]:
        valid_dataloader = build_dataloader(config, "Eval", device, logger)
    else:
        valid_dataloader = None

    # build post process
    post_process_class = build_post_process(config["PostProcess"], global_config)

    # build model
    # for rec algorithm
    model = build_model(config["Architecture"])
    model.to(device)

    # build loss
    loss_class = build_loss(config["Loss"])

    # build optim
    optimizer, lr_scheduler = build_optimizer(
        config["Optimizer"],
        epochs=config["Global"]["epoch_num"],
        step_each_epoch=len(train_dataloader),
        model=model,
    )

    # build metric
    eval_class = build_metric(config["Metric"])

    logger.info("train dataloader has {} iters".format(len(train_dataloader)))
    if valid_dataloader is not None:
        logger.info("valid dataloader has {} iters".format(len(valid_dataloader)))

    # load pretrain model
    pre_best_model_dict = load_model(config, model, optimizer)

    if config["Global"]["distributed"]:
        model = torch.nn.parallel.DistributedDataParallel(
            model, device_ids=[config["local_rank"]]
        )
    # start train
    program.train(
        config,
        train_dataloader,
        valid_dataloader,
        device,
        model,
        loss_class,
        optimizer,
        lr_scheduler,
        post_process_class,
        eval_class,
        pre_best_model_dict,
        logger,
        log_writer,
    )


if __name__ == "__main__":
    config, device, logger, log_writer = program.preprocess(is_train=True)
    seed = config["Global"]["seed"] if "seed" in config["Global"] else 1024
    set_seed(seed)
    main(config, device, logger, log_writer)
