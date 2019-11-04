import torch
import numpy as np

# inspired by fastai course

# helpers for lossss

def hw2corners(ctr, hw): return torch.cat([ctr-hw/2, ctr+hw/2], dim=1)

def intersect(box_a, box_b):
    """ Returns the intersection of two boxes """
    max_xy = torch.min(box_a[:, None, 2:], box_b[None, :, 2:])
    min_xy = torch.max(box_a[:, None, :2], box_b[None, :, :2])
    inter = torch.clamp((max_xy - min_xy), min=0)
    return inter[:, :, 0] * inter[:, :, 1]

def box_sz(b): 
    """ Returns the box size"""
    return ((b[:, 2]-b[:, 0]) * (b[:, 3]-b[:, 1]))

def jaccard(box_a, box_b):
    """ Returns the jaccard distance between two boxes"""
    inter = intersect(box_a, box_b)
    union = box_sz(box_a).unsqueeze(1) + box_sz(box_b).unsqueeze(0) - inter
    return inter / union

def get_y(bbox,clas):
    """ ??? """
    bbox = bbox.view(-1,4)/224
    bb_keep = ((bbox[:,2]-bbox[:,0])>0).nonzero()[:,0]
    return bbox[bb_keep],clas[bb_keep]

def actn_to_bb(actn, anchors, grid_sizes):
    """ activations to bounding boxes """
    actn_bbs = torch.tanh(actn)
    actn_centers = (actn_bbs[:,:2]/2 * grid_sizes) + anchors[:,:2]
    actn_hw = (actn_bbs[:,2:]/2+1) * anchors[:,2:]
    return hw2corners(actn_centers, actn_hw)

def map_to_ground_truth(overlaps):
    """ ?? """
    prior_overlap, prior_idx = overlaps.max(1)
    gt_overlap, gt_idx = overlaps.max(0)
    gt_overlap[prior_idx] = 1.99
    for i,o in enumerate(prior_idx): gt_idx[o] = i
    return gt_overlap,gt_idx

def create_anchors():
    anc_grid = 4
    k = 1

    anc_offset = 1/(anc_grid*2)
    anc_x = np.repeat(np.linspace(anc_offset, 1-anc_offset, anc_grid), anc_grid)
    anc_y = np.tile(np.linspace(anc_offset, 1-anc_offset, anc_grid), anc_grid)

    anc_ctrs = np.tile(np.stack([anc_x,anc_y], axis=1), (k,1))
    anc_sizes = np.array([[1/anc_grid,1/anc_grid] for i in range(anc_grid*anc_grid)])
    anchors = torch.from_numpy(np.concatenate([anc_ctrs, anc_sizes], axis=1)).float()

    grid_sizes = torch.from_numpy(np.array([1/anc_grid])).unsqueeze(1)
    
    return anchors, grid_sizes

# helper for dataset

def prepare_gt(y, x):
    '''
    bring gt bboxes in correct format and scales values to [0,1]
    '''
    
    gt_bbox, gt_clas = [], []
    for obj in y:
        gt_bbox.append(obj['bbox'])
        gt_clas.append(obj['category_id'])
    gt = [torch.FloatTensor(gt_bbox), torch.IntTensor(gt_clas)]
    
    print(x.size)
    
    x_size, y_size = x.shape[2], x.shape[1]
    for idx, bbox in enumerate(gt[0]):
        new_bbox = [0] * 4
        new_bbox[0] = min(bbox[0], bbox[2]) / x_size
        new_bbox[2] = max(bbox[0], bbox[2]) / x_size
        new_bbox[1] = min(bbox[1], bbox[3]) / y_size
        new_bbox[3] = max(bbox[1], bbox[3]) / y_size
        gt[0][idx] = torch.FloatTensor(new_bbox)
    return gt

# helper for train
def print_batch_stats(epoch, batch_idx, train_loader, batch_loss, params):
    '''
    prints statistics about the recently seen batches
    '''
    print('Epoch: {} of {}'.format(epoch, params.n_epochs))
    print('Batch: {} of {}'.format(batch_idx, len(train_loader))
    print('Batch_loss: {}'.format(batch_loss))
        
                          
def evaluate(model, valid_loader, epoch_loss, device, params):
    '''
    evaluates model performance of the validation set, saves current set if it is better that the best so far
    '''       
    model.eval()
    with torch.no_grad():
        val_loss = 0.0
        for batch_idx, (input_, label) in enumerate(valid_loader):      

            input_ = input_.to(device)
            label[0], label[1] = label[0].to(device), label[1].to(device)

            output = model(input_)
            loss = ssd_loss(output,label)
            val_loss += loss.item()
          
            # metric of performance...
              
