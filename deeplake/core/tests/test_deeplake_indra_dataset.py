import deeplake
import numpy as np
from deeplake.tests.common import requires_libdeeplake
from deeplake.util.exceptions import DynamicTensorNumpyError
from deeplake.core.dataset.deeplake_query_dataset import DeepLakeQueryDataset
import random
import pytest


@requires_libdeeplake
def test_indexing(hub_cloud_ds_generator):
    from deeplake.enterprise.convert_to_libdeeplake import dataset_to_libdeeplake

    deeplake_ds = hub_cloud_ds_generator()
    with deeplake_ds:
        deeplake_ds.create_tensor("label", htype="generic", dtype=np.int32)
        for i in range(1000):
            deeplake_ds.label.append(int(100 * random.uniform(0.0, 1.0)))

    indra_ds = dataset_to_libdeeplake(deeplake_ds)
    deeplake_indra_ds = DeepLakeQueryDataset(deeplake_ds=deeplake_ds, indra_ds=indra_ds)

    assert len(deeplake_indra_ds) == len(indra_ds)

    # test slice indices
    assert np.all(deeplake_indra_ds.label.numpy() == indra_ds.label.numpy())
    assert np.all(deeplake_indra_ds.label[5:55].numpy() == indra_ds.label[5:55].numpy())

    assert np.all(deeplake_indra_ds[5:55].label.numpy() == indra_ds.label[5:55].numpy())

    # test int indices
    assert np.all(deeplake_indra_ds.label[0].numpy() == indra_ds.label[0].numpy())

    assert np.all(deeplake_indra_ds[0].label.numpy() == indra_ds.label[0].numpy())

    # test list indices
    assert np.all(
        deeplake_indra_ds.label[[0, 1]].numpy() == indra_ds.label[[0, 1]].numpy()
    )

    assert np.all(
        deeplake_indra_ds[[0, 1]].label.numpy() == indra_ds.label[[0, 1]].numpy()
    )

    # test tuple indices
    assert np.all(
        deeplake_indra_ds[(0, 1),].label.numpy() == indra_ds.label[(0, 1),].numpy()
    )

    assert np.all(
        deeplake_indra_ds[(0, 1),].label.numpy() == indra_ds.label[(0, 1),].numpy()
    )


@requires_libdeeplake
def test_save_view(hub_cloud_ds_generator):
    from deeplake.enterprise.convert_to_libdeeplake import dataset_to_libdeeplake

    deeplake_ds = hub_cloud_ds_generator()
    with deeplake_ds:
        deeplake_ds.create_tensor("label", htype="generic", dtype=np.int32)
        for i in range(1000):
            deeplake_ds.label.append(int(100 * random.uniform(0.0, 1.0)))

    deeplake_ds.commit("First")

    indra_ds = dataset_to_libdeeplake(deeplake_ds)
    deeplake_indra_ds = DeepLakeQueryDataset(deeplake_ds=deeplake_ds, indra_ds=indra_ds)
    deeplake_indra_ds.save_view()
    assert (
        deeplake_indra_ds.base_storage["queries.json"]
        == deeplake_ds.base_storage["queries.json"]
    )


@requires_libdeeplake
def test_load_view(hub_cloud_ds_generator):
    from deeplake.enterprise.convert_to_libdeeplake import dataset_to_libdeeplake

    deeplake_ds = hub_cloud_ds_generator()
    with deeplake_ds:
        deeplake_ds.create_tensor("label", htype="generic", dtype=np.int32)
        deeplake_ds.create_tensor(
            "image", htype="image", dtype=np.uint8, sample_compression="jpg"
        )
        for i in range(100):
            deeplake_ds.label.append(i % 10)
            deeplake_ds.image.append(np.random.randint(0, 255, (100, 200, 3), np.uint8))

    deeplake_ds.commit("First")

    indra_ds = dataset_to_libdeeplake(deeplake_ds)
    deeplake_indra_ds = DeepLakeQueryDataset(deeplake_ds=deeplake_ds, indra_ds=indra_ds)

    with pytest.raises(Exception):
        dataloader = deeplake_indra_ds.pytorch()

    query_str = "select * group by label"
    view = deeplake_ds.query(query_str)
    view_path = view.save_view()
    view_id = view_path.split("/")[-1]
    view = deeplake_ds.load_view(view_id)

    dataloader = view[:3].dataloader().pytorch()
    iss = []
    for i, batch in enumerate(dataloader):
        assert len(batch["label"]) == 10
        iss.append(i)

    assert iss == [0, 1, 2]
    assert np.all(indra_ds.image.numpy() == deeplake_indra_ds.image.numpy())

    view = deeplake_ds[0:50].query(query_str)
    view_path = view.save_view()
    view_id = view_path.split("/")[-1]
    view = deeplake_ds.load_view(view_id)

    dataloader = view[:3].dataloader().pytorch()
    iss = []
    for i, batch in enumerate(dataloader):
        assert len(batch["label"]) == 5
        iss.append(i)

    assert iss == [0, 1, 2]
    assert np.all(indra_ds.image.numpy() == deeplake_indra_ds.image.numpy())


@requires_libdeeplake
def test_query(hub_cloud_ds_generator):
    from deeplake.enterprise.convert_to_libdeeplake import dataset_to_libdeeplake

    deeplake_ds = hub_cloud_ds_generator()
    with deeplake_ds:
        deeplake_ds.create_tensor("label", htype="generic", dtype=np.int32)
        deeplake_ds.create_tensor(
            "image", htype="image", dtype=np.uint8, sample_compression="jpg"
        )
        for i in range(100):
            deeplake_ds.label.append(int(i / 10))
            deeplake_ds.image.append(np.random.randint(0, 255, (100, 200, 3), np.uint8))

    indra_ds = dataset_to_libdeeplake(deeplake_ds)
    deeplake_indra_ds = DeepLakeQueryDataset(deeplake_ds=deeplake_ds, indra_ds=indra_ds)

    view = deeplake_indra_ds.query("SELECT * GROUP BY label")
    assert len(view) == 10
    for i in range(len(view)):
        arr = view.label[i].numpy()
        assert len(arr) == 10
        for a in arr:
            assert np.all(a == i)

    view2 = view.query("SELECT * WHERE all(label == 2)")
    assert len(view2) == 1
    arr = view2.label.numpy()
    assert len(arr) == 10
    for a in arr:
        assert np.all(a == 2)


@requires_libdeeplake
def test_metadata(hub_cloud_ds_generator):
    from deeplake.enterprise.convert_to_libdeeplake import dataset_to_libdeeplake

    deeplake_ds = hub_cloud_ds_generator()
    with deeplake_ds:
        deeplake_ds.create_tensor("label", htype="generic", dtype=np.int32)
        deeplake_ds.create_tensor(
            "image", htype="image", dtype=np.uint8, sample_compression="jpeg"
        )
        deeplake_ds.create_tensor("none_metadata")
        deeplake_ds.create_tensor(
            "sequence", htype="sequence[class_label]", dtype=np.uint8
        )

    indra_ds = dataset_to_libdeeplake(deeplake_ds)
    deeplake_indra_ds = DeepLakeQueryDataset(deeplake_ds=deeplake_ds, indra_ds=indra_ds)
    assert deeplake_indra_ds.label.htype == "generic"
    assert deeplake_indra_ds.label.dtype == np.int32
    assert deeplake_indra_ds.label.sample_compression == None
    assert deeplake_indra_ds.image.htype == "image"
    assert deeplake_indra_ds.image.dtype == np.uint8
    assert deeplake_indra_ds.image.sample_compression == "jpg"
    assert deeplake_indra_ds.sequence.htype == "sequence[class_label]"
    assert deeplake_indra_ds.sequence.dtype == np.uint8
    assert deeplake_indra_ds.sequence.sample_compression == None
    assert deeplake_indra_ds.none_metadata.htype == None
    assert deeplake_indra_ds.none_metadata.dtype == None
    assert deeplake_indra_ds.none_metadata.sample_compression == None


@requires_libdeeplake
def test_accessing_data(hub_cloud_ds_generator):
    from deeplake.enterprise.convert_to_libdeeplake import dataset_to_libdeeplake

    deeplake_ds = hub_cloud_ds_generator()
    with deeplake_ds:
        deeplake_ds.create_tensor("label", htype="generic", dtype=np.int32)
        for i in range(1000):
            deeplake_ds.label.append(int(100 * random.uniform(0.0, 1.0)))

    indra_ds = dataset_to_libdeeplake(deeplake_ds)
    deeplake_indra_ds = DeepLakeQueryDataset(deeplake_ds=deeplake_ds, indra_ds=indra_ds)

    assert np.all(
        np.isclose(deeplake_indra_ds.label.numpy(), deeplake_indra_ds["label"].numpy())
    )


@requires_libdeeplake
def test_sequences_accessing_data(hub_cloud_ds_generator):
    deeplake_ds = hub_cloud_ds_generator()
    with deeplake_ds:
        deeplake_ds.create_tensor("label", htype="generic", dtype=np.int32)
        for i in range(200):
            deeplake_ds.label.append(int(i / 101))
        deeplake_ds.create_tensor(
            "image", htype="image", sample_compression="jpeg", dtype=np.uint8
        )
        for i in range(199):
            deeplake_ds.image.append(np.zeros((10, 10, 3), dtype=np.uint8))
        deeplake_ds.image.append(np.zeros((20, 10, 3), np.uint8))

    deeplake_indra_ds = deeplake_ds.query("SELECT * GROUP BY label")
    assert len(deeplake_indra_ds) == 2
    assert deeplake_indra_ds.image.shape == [2, None, None, 10, 3]
    assert deeplake_indra_ds[0].image.shape == [101, 10, 10, 3]
    assert deeplake_indra_ds[0, 0].image.shape == [10, 10, 3]
    assert deeplake_indra_ds[0].image.numpy().shape == (101, 10, 10, 3)
    assert deeplake_indra_ds[1].image.shape == [99, None, 10, 3]
    assert deeplake_indra_ds[1, 0].image.shape == [10, 10, 3]
    assert deeplake_indra_ds[1, 98].image.shape == [20, 10, 3]
    assert deeplake_indra_ds[1].image.numpy().shape == (99,)
    assert deeplake_indra_ds[1].image.numpy()[0].shape == (10, 10, 3)
    assert deeplake_indra_ds[1].image.numpy()[98].shape == (20, 10, 3)


@requires_libdeeplake
def test_random_split(hub_cloud_ds_generator):
    deeplake_ds = hub_cloud_ds_generator()
    with deeplake_ds:
        deeplake_ds.create_tensor("label", htype="generic", dtype=np.int32)
        for i in range(1000):
            deeplake_ds.label.append(int(i % 100))

    deeplake_indra_ds = deeplake_ds.query("SELECT * GROUP BY label")

    split = deeplake_indra_ds.random_split([0.2, 0.2, 0.6])
    assert len(split) == 3
    assert len(split[0]) == 20
    l = split[0].dataloader().pytorch()
    for b in l:
        pass
    assert len(split[1]) == 20
    l = split[1].dataloader().pytorch()
    for b in l:
        pass
    assert len(split[2]) == 60
    l = split[1].dataloader().pytorch()
    for b in l:
        pass

    split = deeplake_indra_ds.random_split([30, 20, 10, 40])
    assert len(split) == 4
    assert len(split[0]) == 30
    assert len(split[1]) == 20
    assert len(split[2]) == 10
    assert len(split[3]) == 40

    train, val = deeplake_indra_ds[0:50].random_split([0.8, 0.2])
    assert len(train) == 40
    l = train.dataloader().pytorch().shuffle()
    for b in l:
        pass
    assert len(val) == 10
    l = val.dataloader().pytorch().shuffle()
    for b in l:
        pass


@requires_libdeeplake
def test_virtual_tensors(hub_cloud_ds_generator):
    deeplake_ds = hub_cloud_ds_generator()
    with deeplake_ds:
        deeplake_ds.create_tensor("label", htype="generic", dtype=np.int32)
        deeplake_ds.create_tensor("embeddings", htype="generic", dtype=np.float32)
        for i in range(100):
            count = i % 5
            deeplake_ds.label.append([int(i % 100)] * count)
            deeplake_ds.embeddings.append(
                [1.0 / float(i + 1), 0.0, -1.0 / float(i + 1)]
            )

    deeplake_indra_ds = deeplake_ds.query("SELECT shape(label)[0] as num_labels")
    assert len(deeplake_indra_ds) == 100
    assert deeplake_indra_ds.num_labels[0].numpy() == [0]
    assert deeplake_indra_ds.num_labels[1].numpy() == [1]
    assert deeplake_indra_ds.num_labels[2].numpy() == [2]
    assert deeplake_indra_ds.num_labels[3].numpy() == [3]
    assert deeplake_indra_ds.num_labels[4].numpy() == [4]
    assert np.sum(deeplake_indra_ds.num_labels.numpy()) == 200

    deeplake_indra_ds = deeplake_ds.query(
        "SELECT l2_norm(embeddings - ARRAY[0, 0, 0]) as score order by l2_norm(embeddings - ARRAY[0, 0, 0]) asc"
    )
    assert len(deeplake_indra_ds) == 100
    for i in range(100, 1):
        assert deeplake_indra_ds.score[100 - i].numpy() == [
            np.sqrt(2.0 / (i + 1) / (i + 1))
        ]
