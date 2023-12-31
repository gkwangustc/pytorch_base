from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np

import os
import sys

__dir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.append(__dir__)
sys.path.insert(0, os.path.abspath(os.path.join(__dir__, "..")))

os.environ["FLAGS_allocator_strategy"] = "auto_growth"

import torch

from core.data import create_operators, transform
from core.modeling import build_model
from core.postprocess import build_post_process
from core.utils.save_load import load_model
from core.utils.utility import get_image_file_list
import tools.program as program


def main():
    global_config = config["Global"]

    # build post process
    post_process_class = build_post_process(config["PostProcess"], global_config)

    # build model
    model = build_model(config["Architecture"])

    load_model(config, model)

    # create data ops
    transforms = []
    for op in config["Eval"]["dataset"]["transforms"]:
        op_name = list(op)[0]
        if "Label" in op_name:
            continue
        elif op_name == "KeepKeys":
            op[op_name]["keep_keys"] = ["image"]
        transforms.append(op)
    global_config["infer_mode"] = True
    ops = create_operators(transforms, global_config)

    model.eval()
    for file in get_image_file_list(config["Global"]["infer_img"]):
        logger.info("infer_img: {}".format(file))
        with open(file, "rb") as f:
            img = f.read()
            data = {"image": img}
        batch = transform(data, ops)

        images = np.expand_dims(batch[0], axis=0)
        images = torch.tensor(images)
        preds = model(images)
        post_result = post_process_class(preds)
        for rec_result in post_result:
            logger.info("\t result: {}".format(rec_result))
    logger.info("success!")


if __name__ == "__main__":
    config, device, logger, log_writer = program.preprocess()
    main()
