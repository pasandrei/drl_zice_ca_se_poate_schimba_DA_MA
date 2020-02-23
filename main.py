from torch.utils.tensorboard import SummaryWriter
from train.loss_fn import Detection_Loss
import torch
import random

from train import train
from train.params import Params
from train.validate import Model_evaluator
from misc import cross_validation
from misc.model_output_handler import Model_output_handler
from jaad_data import inference
from general_config import path_config

from utils import prints
from utils import training


def run(model_id="ssdlite", train_model=False, load_checkpoint=False, eval_only=False, cross_validate=False, jaad=False):
    """
    Arguments:
    model_id - id of the model to be trained
    train_model - training
    load_checkpoint - load a pretrained model
    eval_only - only inference
    cross_validate - cross validate for best nms thresold and positive confidence
    jaad - inference on jaad videos
    """
    torch.manual_seed(2)
    random.seed(2)

    params = Params(path_config.params_path.format(model_id))
    stats = Params(path_config.stats_path.format(model_id))

    prints.show_training_info(params)

    train_loader, valid_loader = training.prepare_datasets(params)
    prints.print_dataset_stats(train_loader, valid_loader)

    model = training.model_setup(params)
    optimizer = training.optimizer_setup(model, params)

    if jaad:
        model, _, _ = training.load_model(model, params, optimizer)
        handler = Model_output_handler(params)
        inference.jaad_inference(model, handler)

    # tensorboard
    writer = SummaryWriter(filename_suffix=params.model_id)

    detection_loss = Detection_Loss(params)
    model_evaluator = Model_evaluator(valid_loader, detection_loss,
                                      writer=writer, params=params, stats=stats)

    start_epoch = 0
    if load_checkpoint:
        model, optimizer, start_epoch = training.load_model(model, params, optimizer)

    prints.print_trained_parameters_count(model, optimizer)

    if eval_only:
        model_evaluator.complete_evaluate(model, optimizer, train_loader)

    if cross_validate:
        cross_validation.cross_validate(
            model, detection_loss, valid_loader, model_evaluator, params)

    if train_model:
        train.train(model, optimizer, train_loader, model_evaluator,
                    detection_loss, params, start_epoch)
